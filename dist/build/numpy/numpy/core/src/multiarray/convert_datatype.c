#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"

#define _MULTIARRAYMODULE
#define NPY_NO_PREFIX
#include "numpy/arrayobject.h"
#include "numpy/arrayscalars.h"

#include "npy_config.h"

#include "numpy/npy_3kcompat.h"

#include "common.h"
#include "scalartypes.h"
#include "mapping.h"

#include "convert_datatype.h"

/*NUMPY_API
 * For backward compatibility
 *
 * Cast an array using typecode structure.
 * steals reference to at --- cannot be NULL
 *
 * This function always makes a copy of arr, even if the dtype
 * doesn't change.
 */
NPY_NO_EXPORT PyObject *
PyArray_CastToType(PyArrayObject *arr, PyArray_Descr *dtype, int fortran)
{
    PyObject *out;
    PyArray_Descr *arr_dtype;

    arr_dtype = PyArray_DESCR(arr);

    if (dtype->elsize == 0) {
        PyArray_DESCR_REPLACE(dtype);
        if (dtype == NULL) {
            return NULL;
        }

        if (arr_dtype->type_num == dtype->type_num) {
            dtype->elsize = arr_dtype->elsize;
        }
        else if (arr_dtype->type_num == NPY_STRING &&
                                dtype->type_num == NPY_UNICODE) {
            dtype->elsize = arr_dtype->elsize * 4;
        }
        else if (arr_dtype->type_num == NPY_UNICODE &&
                                dtype->type_num == NPY_STRING) {
            dtype->elsize = arr_dtype->elsize / 4;
        }
        else if (dtype->type_num == NPY_VOID) {
            dtype->elsize = arr_dtype->elsize;
        }
    }

    out = PyArray_NewFromDescr(Py_TYPE(arr), dtype,
                               arr->nd,
                               arr->dimensions,
                               NULL, NULL,
                               fortran,
                               (PyObject *)arr);

    if (out == NULL) {
        return NULL;
    }

    if (PyArray_CopyInto((PyArrayObject *)out, arr) < 0) {
        Py_DECREF(out);
        return NULL;
    }

    return out;
}

/*NUMPY_API
 * Get a cast function to cast from the input descriptor to the
 * output type_number (must be a registered data-type).
 * Returns NULL if un-successful.
 */
NPY_NO_EXPORT PyArray_VectorUnaryFunc *
PyArray_GetCastFunc(PyArray_Descr *descr, int type_num)
{
    PyArray_VectorUnaryFunc *castfunc = NULL;

    if (type_num < NPY_NTYPES_ABI_COMPATIBLE) {
        castfunc = descr->f->cast[type_num];
    }
    else {
        PyObject *obj = descr->f->castdict;
        if (obj && PyDict_Check(obj)) {
            PyObject *key;
            PyObject *cobj;

            key = PyInt_FromLong(type_num);
            cobj = PyDict_GetItem(obj, key);
            Py_DECREF(key);
            if (NpyCapsule_Check(cobj)) {
                castfunc = NpyCapsule_AsVoidPtr(cobj);
            }
        }
    }
    if (PyTypeNum_ISCOMPLEX(descr->type_num) &&
        !PyTypeNum_ISCOMPLEX(type_num) &&
        PyTypeNum_ISNUMBER(type_num) &&
        !PyTypeNum_ISBOOL(type_num)) {
        PyObject *cls = NULL, *obj = NULL;
        int ret;
        obj = PyImport_ImportModule("numpy.core");
        if (obj) {
            cls = PyObject_GetAttrString(obj, "ComplexWarning");
            Py_DECREF(obj);
        }
#if PY_VERSION_HEX >= 0x02050000
        ret = PyErr_WarnEx(cls,
                           "Casting complex values to real discards "
                           "the imaginary part", 1);
#else
        ret = PyErr_Warn(cls,
                         "Casting complex values to real discards "
                         "the imaginary part");
#endif
        Py_XDECREF(cls);
        if (ret < 0) {
            return NULL;
	    }
    }
    if (castfunc) {
        return castfunc;
    }

    PyErr_SetString(PyExc_ValueError, "No cast function available.");
    return NULL;
}

/*
 * Must be broadcastable.
 * This code is very similar to PyArray_CopyInto/PyArray_MoveInto
 * except casting is done --- PyArray_BUFSIZE is used
 * as the size of the casting buffer.
 */

/*NUMPY_API
 * Cast to an already created array.
 */
NPY_NO_EXPORT int
PyArray_CastTo(PyArrayObject *out, PyArrayObject *mp)
{
    /* CopyInto handles the casting now */
    return PyArray_CopyInto(out, mp);
}

/*NUMPY_API
 * Cast to an already created array.  Arrays don't have to be "broadcastable"
 * Only requirement is they have the same number of elements.
 */
NPY_NO_EXPORT int
PyArray_CastAnyTo(PyArrayObject *out, PyArrayObject *mp)
{
    /* CopyAnyInto handles the casting now */
    return PyArray_CopyAnyInto(out, mp);
}

/*NUMPY_API
 *Check the type coercion rules.
 */
NPY_NO_EXPORT int
PyArray_CanCastSafely(int fromtype, int totype)
{
    PyArray_Descr *from;

    /* Fast table lookup for small type numbers */
    if ((unsigned int)fromtype < NPY_NTYPES &&
                                (unsigned int)totype < NPY_NTYPES) {
        return _npy_can_cast_safely_table[fromtype][totype];
    }

    /* Identity */
    if (fromtype == totype) {
        return 1;
    }
    /* Special-cases for some types */
    switch (fromtype) {
        case PyArray_DATETIME:
        case PyArray_TIMEDELTA:
        case PyArray_OBJECT:
        case PyArray_VOID:
            return 0;
        case PyArray_BOOL:
            return 1;
    }
    switch (totype) {
        case PyArray_BOOL:
        case PyArray_DATETIME:
        case PyArray_TIMEDELTA:
            return 0;
        case PyArray_OBJECT:
        case PyArray_VOID:
            return 1;
    }

    from = PyArray_DescrFromType(fromtype);
    /*
     * cancastto is a PyArray_NOTYPE terminated C-int-array of types that
     * the data-type can be cast to safely.
     */
    if (from->f->cancastto) {
        int *curtype = from->f->cancastto;

        while (*curtype != PyArray_NOTYPE) {
            if (*curtype++ == totype) {
                return 1;
            }
        }
    }
    return 0;
}

/*NUMPY_API
 * leaves reference count alone --- cannot be NULL
 *
 * PyArray_CanCastTypeTo is equivalent to this, but adds a 'casting'
 * parameter.
 */
NPY_NO_EXPORT npy_bool
PyArray_CanCastTo(PyArray_Descr *from, PyArray_Descr *to)
{
    int fromtype=from->type_num;
    int totype=to->type_num;
    npy_bool ret;

    ret = (npy_bool) PyArray_CanCastSafely(fromtype, totype);
    if (ret) {
        /* Check String and Unicode more closely */
        if (fromtype == PyArray_STRING) {
            if (totype == PyArray_STRING) {
                ret = (from->elsize <= to->elsize);
            }
            else if (totype == PyArray_UNICODE) {
                ret = (from->elsize << 2 <= to->elsize);
            }
        }
        else if (fromtype == PyArray_UNICODE) {
            if (totype == PyArray_UNICODE) {
                ret = (from->elsize <= to->elsize);
            }
        }
        /*
         * TODO: If totype is STRING or unicode
         * see if the length is long enough to hold the
         * stringified value of the object.
         */
    }
    return ret;
}

/* Provides an ordering for the dtype 'kind' character codes */
static int
dtype_kind_to_ordering(char kind)
{
    switch (kind) {
        /* Boolean kind */
        case 'b':
            return 0;
        /* Unsigned int kind */
        case 'u':
            return 1;
        /* Signed int kind */
        case 'i':
            return 2;
        /* Float kind */
        case 'f':
            return 4;
        /* Complex kind */
        case 'c':
            return 5;
        /* String kind */
        case 'S':
        case 'a':
            return 6;
        /* Unicode kind */
        case 'U':
            return 7;
        /* Void kind */
        case 'V':
            return 8;
        /* Object kind */
        case 'O':
            return 9;
        /* Anything else - ideally shouldn't happen... */
        default:
            return 10;
    }
}

/* Converts a type number from unsigned to signed */
static int
type_num_unsigned_to_signed(int type_num)
{
    switch (type_num) {
        case NPY_UBYTE:
            return NPY_BYTE;
        case NPY_USHORT:
            return NPY_SHORT;
        case NPY_UINT:
            return NPY_INT;
        case NPY_ULONG:
            return NPY_LONG;
        case NPY_ULONGLONG:
            return NPY_LONGLONG;
        default:
            return type_num;
    }
}

/*NUMPY_API
 * Returns true if data of type 'from' may be cast to data of type
 * 'to' according to the rule 'casting'.
 */
NPY_NO_EXPORT npy_bool
PyArray_CanCastTypeTo(PyArray_Descr *from, PyArray_Descr *to,
                                                    NPY_CASTING casting)
{
    /* If unsafe casts are allowed */
    if (casting == NPY_UNSAFE_CASTING) {
        return 1;
    }
    /* Equivalent types can be cast with any value of 'casting'  */
    else if (PyArray_EquivTypenums(from->type_num, to->type_num)) {
        /* For complicated case, use EquivTypes (for now) */
        if (PyTypeNum_ISUSERDEF(from->type_num) ||
                        PyDataType_HASFIELDS(from) ||
                        from->subarray != NULL) {
            int ret;

            /* Only NPY_NO_CASTING prevents byte order conversion */
            if ((casting != NPY_NO_CASTING) &&
                                (!PyArray_ISNBO(from->byteorder) ||
                                 !PyArray_ISNBO(to->byteorder))) {
                PyArray_Descr *nbo_from, *nbo_to;

                nbo_from = PyArray_DescrNewByteorder(from, NPY_NATIVE);
                nbo_to = PyArray_DescrNewByteorder(to, NPY_NATIVE);
                if (nbo_from == NULL || nbo_to == NULL) {
                    Py_XDECREF(nbo_from);
                    Py_XDECREF(nbo_to);
                    PyErr_Clear();
                    return 0;
                }
                ret = PyArray_EquivTypes(nbo_from, nbo_to);
                Py_DECREF(nbo_from);
                Py_DECREF(nbo_to);
            }
            else {
                ret = PyArray_EquivTypes(from, to);
            }
            return ret;
        }

        switch (casting) {
            case NPY_NO_CASTING:
                return (from->elsize == to->elsize) &&
                        PyArray_ISNBO(from->byteorder) ==
                                    PyArray_ISNBO(to->byteorder);
            case NPY_EQUIV_CASTING:
                return (from->elsize == to->elsize);
            case NPY_SAFE_CASTING:
                return (from->elsize <= to->elsize);
            default:
                return 1;
        }
    }
    /* If safe or same-kind casts are allowed */
    else if (casting == NPY_SAFE_CASTING || casting == NPY_SAME_KIND_CASTING) {
        if (PyArray_CanCastTo(from, to)) {
            return 1;
        }
        else if(casting == NPY_SAME_KIND_CASTING) {
            /*
             * Also allow casting from lower to higher kinds, according
             * to the ordering provided by dtype_kind_to_ordering.
             */
            return dtype_kind_to_ordering(from->kind) <=
                            dtype_kind_to_ordering(to->kind);
        }
        else {
            return 0;
        }
    }
    /* NPY_NO_CASTING or NPY_EQUIV_CASTING was specified */
    else {
        return 0;
    }
}

/* CanCastArrayTo needs this function */
static int min_scalar_type_num(char *valueptr, int type_num,
                                            int *is_small_unsigned);

/*NUMPY_API
 * Returns 1 if the array object may be cast to the given data type using
 * the casting rule, 0 otherwise.  This differs from PyArray_CanCastTo in
 * that it handles scalar arrays (0 dimensions) specially, by checking
 * their value.
 */
NPY_NO_EXPORT npy_bool
PyArray_CanCastArrayTo(PyArrayObject *arr, PyArray_Descr *to,
                        NPY_CASTING casting)
{
    PyArray_Descr *from = PyArray_DESCR(arr);

    /* If it's not a scalar, use the standard rules */
    if (PyArray_NDIM(arr) > 0 || !PyTypeNum_ISNUMBER(from->type_num)) {
        return PyArray_CanCastTypeTo(from, to, casting);
    }
    /* Otherwise, check the value */
    else {
        int swap = !PyArray_ISNBO(from->byteorder);
        int is_small_unsigned = 0, type_num;
        npy_bool ret;
        PyArray_Descr *dtype;

        /* An aligned memory buffer large enough to hold any type */
        npy_longlong value[4];

        from->f->copyswap(&value, PyArray_BYTES(arr), swap, NULL);

        type_num = min_scalar_type_num((char *)&value, from->type_num,
                                        &is_small_unsigned);

        /*
         * If we've got a small unsigned scalar, and the 'to' type
         * is not unsigned, then make it signed to allow the value
         * to be cast more appropriately.
         */
        if (is_small_unsigned && !(PyTypeNum_ISUNSIGNED(to->type_num))) {
            type_num = type_num_unsigned_to_signed(type_num);
        }

        dtype = PyArray_DescrFromType(type_num);
        if (dtype == NULL) {
            return 0;
        }
#if 0
        printf("min scalar cast ");
        PyObject_Print(dtype, stdout, 0);
        printf(" to ");
        PyObject_Print(to, stdout, 0);
        printf("\n");
#endif
        ret = PyArray_CanCastTypeTo(dtype, to, casting);
        Py_DECREF(dtype);
        return ret;
    }
}

/*NUMPY_API
 * See if array scalars can be cast.
 *
 * TODO: For NumPy 2.0, add a NPY_CASTING parameter.
 */
NPY_NO_EXPORT npy_bool
PyArray_CanCastScalar(PyTypeObject *from, PyTypeObject *to)
{
    int fromtype;
    int totype;

    fromtype = _typenum_fromtypeobj((PyObject *)from, 0);
    totype = _typenum_fromtypeobj((PyObject *)to, 0);
    if (fromtype == PyArray_NOTYPE || totype == PyArray_NOTYPE) {
        return FALSE;
    }
    return (npy_bool) PyArray_CanCastSafely(fromtype, totype);
}

/*
 * Internal promote types function which handles unsigned integers which
 * fit in same-sized signed integers specially.
 */
static PyArray_Descr *
promote_types(PyArray_Descr *type1, PyArray_Descr *type2,
                        int is_small_unsigned1, int is_small_unsigned2)
{
    if (is_small_unsigned1) {
        int type_num1 = type1->type_num;
        int type_num2 = type2->type_num;
        int ret_type_num;

        if (type_num2 < NPY_NTYPES && !(PyTypeNum_ISBOOL(type_num2) ||
                                        PyTypeNum_ISUNSIGNED(type_num2))) {
            /* Convert to the equivalent-sized signed integer */
            type_num1 = type_num_unsigned_to_signed(type_num1);

            ret_type_num = _npy_type_promotion_table[type_num1][type_num2];
            /* The table doesn't handle string/unicode/void, check the result */
            if (ret_type_num >= 0) {
                return PyArray_DescrFromType(ret_type_num);
            }
        }

        return PyArray_PromoteTypes(type1, type2);
    }
    else if (is_small_unsigned2) {
        int type_num1 = type1->type_num;
        int type_num2 = type2->type_num;
        int ret_type_num;

        if (type_num1 < NPY_NTYPES && !(PyTypeNum_ISBOOL(type_num1) ||
                                        PyTypeNum_ISUNSIGNED(type_num1))) {
            /* Convert to the equivalent-sized signed integer */
            type_num2 = type_num_unsigned_to_signed(type_num2);

            ret_type_num = _npy_type_promotion_table[type_num1][type_num2];
            /* The table doesn't handle string/unicode/void, check the result */
            if (ret_type_num >= 0) {
                return PyArray_DescrFromType(ret_type_num);
            }
        }

        return PyArray_PromoteTypes(type1, type2);
    }
    else {
        return PyArray_PromoteTypes(type1, type2);
    }

}

/*NUMPY_API
 * Produces the smallest size and lowest kind type to which both
 * input types can be cast.
 */
NPY_NO_EXPORT PyArray_Descr *
PyArray_PromoteTypes(PyArray_Descr *type1, PyArray_Descr *type2)
{
    int type_num1, type_num2, ret_type_num;

    type_num1 = type1->type_num;
    type_num2 = type2->type_num;

    /* If they're built-in types, use the promotion table */
    if (type_num1 < NPY_NTYPES && type_num2 < NPY_NTYPES) {
        ret_type_num = _npy_type_promotion_table[type_num1][type_num2];
        /* The table doesn't handle string/unicode/void, check the result */
        if (ret_type_num >= 0) {
            return PyArray_DescrFromType(ret_type_num);
        }
    }
    /* If one or both are user defined, calculate it */
    else {
        int skind1 = NPY_NOSCALAR, skind2 = NPY_NOSCALAR, skind;

        if (PyArray_CanCastTo(type2, type1)) {
            /* Promoted types are always native byte order */
            if (PyArray_ISNBO(type1->byteorder)) {
                Py_INCREF(type1);
                return type1;
            }
            else {
                return PyArray_DescrNewByteorder(type1, NPY_NATIVE);
            }
        }
        else if (PyArray_CanCastTo(type1, type2)) {
            /* Promoted types are always native byte order */
            if (PyArray_ISNBO(type2->byteorder)) {
                Py_INCREF(type2);
                return type2;
            }
            else {
                return PyArray_DescrNewByteorder(type2, NPY_NATIVE);
            }
        }

        /* Convert the 'kind' char into a scalar kind */
        switch (type1->kind) {
            case 'b':
                skind1 = NPY_BOOL_SCALAR;
                break;
            case 'u':
                skind1 = NPY_INTPOS_SCALAR;
                break;
            case 'i':
                skind1 = NPY_INTNEG_SCALAR;
                break;
            case 'f':
                skind1 = NPY_FLOAT_SCALAR;
                break;
            case 'c':
                skind1 = NPY_COMPLEX_SCALAR;
                break;
        }
        switch (type2->kind) {
            case 'b':
                skind2 = NPY_BOOL_SCALAR;
                break;
            case 'u':
                skind2 = NPY_INTPOS_SCALAR;
                break;
            case 'i':
                skind2 = NPY_INTNEG_SCALAR;
                break;
            case 'f':
                skind2 = NPY_FLOAT_SCALAR;
                break;
            case 'c':
                skind2 = NPY_COMPLEX_SCALAR;
                break;
        }

        /* If both are scalars, there may be a promotion possible */
        if (skind1 != NPY_NOSCALAR && skind2 != NPY_NOSCALAR) {

            /* Start with the larger scalar kind */
            skind = (skind1 > skind2) ? skind1 : skind2;
            ret_type_num = _npy_smallest_type_of_kind_table[skind];

            for (;;) {

                /* If there is no larger type of this kind, try a larger kind */
                if (ret_type_num < 0) {
                    ++skind;
                    /* Use -1 to signal no promoted type found */
                    if (skind < NPY_NSCALARKINDS) {
                        ret_type_num = _npy_smallest_type_of_kind_table[skind];
                    }
                    else {
                        break;
                    }
                }

                /* If we found a type to which we can promote both, done! */
                if (PyArray_CanCastSafely(type_num1, ret_type_num) &&
                            PyArray_CanCastSafely(type_num2, ret_type_num)) {
                    return PyArray_DescrFromType(ret_type_num);
                }

                /* Try the next larger type of this kind */
                ret_type_num = _npy_next_larger_type_table[ret_type_num];
            }

        }

        PyErr_SetString(PyExc_TypeError,
                "invalid type promotion with custom data type");
        return NULL;
    }

    switch (type_num1) {
        /* BOOL can convert to anything */
        case NPY_BOOL:
            Py_INCREF(type2);
            return type2;
        /* For strings and unicodes, take the larger size */
        case NPY_STRING:
            if (type_num2 == NPY_STRING) {
                if (type1->elsize > type2->elsize) {
                    Py_INCREF(type1);
                    return type1;
                }
                else {
                    Py_INCREF(type2);
                    return type2;
                }
            }
            else if (type_num2 == NPY_UNICODE) {
                if (type2->elsize >= type1->elsize * 4) {
                    Py_INCREF(type2);
                    return type2;
                }
                else {
                    PyArray_Descr *d = PyArray_DescrNewFromType(NPY_UNICODE);
                    if (d == NULL) {
                        return NULL;
                    }
                    d->elsize = type1->elsize * 4;
                    return d;
                }
            }
            /* Allow NUMBER -> STRING */
            else if (PyTypeNum_ISNUMBER(type_num2)) {
                Py_INCREF(type1);
                return type1;
            }
        case NPY_UNICODE:
            if (type_num2 == NPY_UNICODE) {
                if (type1->elsize > type2->elsize) {
                    Py_INCREF(type1);
                    return type1;
                }
                else {
                    Py_INCREF(type2);
                    return type2;
                }
            }
            else if (type_num2 == NPY_STRING) {
                if (type1->elsize >= type2->elsize * 4) {
                    Py_INCREF(type1);
                    return type1;
                }
                else {
                    PyArray_Descr *d = PyArray_DescrNewFromType(NPY_UNICODE);
                    if (d == NULL) {
                        return NULL;
                    }
                    d->elsize = type2->elsize * 4;
                    return d;
                }
            }
            /* Allow NUMBER -> UNICODE */
            else if (PyTypeNum_ISNUMBER(type_num2)) {
                Py_INCREF(type1);
                return type1;
            }
            break;
    }

    switch (type_num2) {
        /* BOOL can convert to anything */
        case NPY_BOOL:
            Py_INCREF(type1);
            return type1;
        case NPY_STRING:
            /* Allow NUMBER -> STRING */
            if (PyTypeNum_ISNUMBER(type_num1)) {
                Py_INCREF(type2);
                return type2;
            }
        case NPY_UNICODE:
            /* Allow NUMBER -> UNICODE */
            if (PyTypeNum_ISNUMBER(type_num1)) {
                Py_INCREF(type2);
                return type2;
            }
            break;
    }

    /* For equivalent types we can return either */
    if (PyArray_EquivTypes(type1, type2)) {
        Py_INCREF(type1);
        return type1;
    }

    /* TODO: Also combine fields, subarrays, strings, etc */

    /*
    printf("invalid type promotion: ");
    PyObject_Print(type1, stdout, 0);
    printf(" ");
    PyObject_Print(type2, stdout, 0);
    printf("\n");
    */
    PyErr_SetString(PyExc_TypeError, "invalid type promotion");
    return NULL;
}

/*
 * NOTE: While this is unlikely to be a performance problem, if
 *       it is it could be reverted to a simple positive/negative
 *       check as the previous system used.
 *
 * The is_small_unsigned output flag indicates whether it's an unsigned integer,
 * and would fit in a signed integer of the same bit size.
 */
static int min_scalar_type_num(char *valueptr, int type_num,
                                            int *is_small_unsigned)
{
    switch (type_num) {
        case NPY_BOOL: {
            return NPY_BOOL;
        }
        case NPY_UBYTE: {
            npy_ubyte value = *(npy_ubyte *)valueptr;
            if (value <= NPY_MAX_BYTE) {
                *is_small_unsigned = 1;
            }
            return NPY_UBYTE;
        }
        case NPY_BYTE: {
            npy_byte value = *(npy_byte *)valueptr;
            if (value >= 0) {
                *is_small_unsigned = 1;
                return NPY_UBYTE;
            }
            break;
        }
        case NPY_USHORT: {
            npy_ushort value = *(npy_ushort *)valueptr;
            if (value <= NPY_MAX_UBYTE) {
                if (value <= NPY_MAX_BYTE) {
                    *is_small_unsigned = 1;
                }
                return NPY_UBYTE;
            }

            if (value <= NPY_MAX_SHORT) {
                *is_small_unsigned = 1;
            }
            break;
        }
        case NPY_SHORT: {
            npy_short value = *(npy_short *)valueptr;
            if (value >= 0) {
                return min_scalar_type_num(valueptr, NPY_USHORT, is_small_unsigned);
            }
            else if (value >= NPY_MIN_BYTE) {
                return NPY_BYTE;
            }
            break;
        }
#if NPY_SIZEOF_LONG == NPY_SIZEOF_INT
        case NPY_ULONG:
#endif
        case NPY_UINT: {
            npy_uint value = *(npy_uint *)valueptr;
            if (value <= NPY_MAX_UBYTE) {
                if (value < NPY_MAX_BYTE) {
                    *is_small_unsigned = 1;
                }
                return NPY_UBYTE;
            }
            else if (value <= NPY_MAX_USHORT) {
                if (value <= NPY_MAX_SHORT) {
                    *is_small_unsigned = 1;
                }
                return NPY_USHORT;
            }

            if (value <= NPY_MAX_INT) {
                *is_small_unsigned = 1;
            }
            break;
        }
#if NPY_SIZEOF_LONG == NPY_SIZEOF_INT
        case NPY_LONG:
#endif
        case NPY_INT: {
            npy_int value = *(npy_int *)valueptr;
            if (value >= 0) {
                return min_scalar_type_num(valueptr, NPY_UINT, is_small_unsigned);
            }
            else if (value >= NPY_MIN_BYTE) {
                return NPY_BYTE;
            }
            else if (value >= NPY_MIN_SHORT) {
                return NPY_SHORT;
            }
            break;
        }
#if NPY_SIZEOF_LONG != NPY_SIZEOF_INT && NPY_SIZEOF_LONG != NPY_SIZEOF_LONGLONG
        case NPY_ULONG: {
            npy_ulong value = *(npy_ulong *)valueptr;
            if (value <= NPY_MAX_UBYTE) {
                if (value <= NPY_MAX_BYTE) {
                    *is_small_unsigned = 1;
                }
                return NPY_UBYTE;
            }
            else if (value <= NPY_MAX_USHORT) {
                if (value <= NPY_MAX_SHORT) {
                    *is_small_unsigned = 1;
                }
                return NPY_USHORT;
            }
            else if (value <= NPY_MAX_UINT) {
                if (value <= NPY_MAX_INT) {
                    *is_small_unsigned = 1;
                }
                return NPY_UINT;
            }

            if (value <= NPY_MAX_LONG) {
                *is_small_unsigned = 1;
            }
            break;
        }
        case NPY_LONG: {
            npy_long value = *(npy_long *)valueptr;
            if (value >= 0) {
                return min_scalar_type_num(valueptr, NPY_ULONG, is_small_unsigned);
            }
            else if (value >= NPY_MIN_BYTE) {
                return NPY_BYTE;
            }
            else if (value >= NPY_MIN_SHORT) {
                return NPY_SHORT;
            }
            else if (value >= NPY_MIN_INT) {
                return NPY_INT;
            }
            break;
        }
#endif
#if NPY_SIZEOF_LONG == NPY_SIZEOF_LONGLONG
        case NPY_ULONG:
#endif
        case NPY_ULONGLONG: {
            npy_ulonglong value = *(npy_ulonglong *)valueptr;
            if (value <= NPY_MAX_UBYTE) {
                if (value <= NPY_MAX_BYTE) {
                    *is_small_unsigned = 1;
                }
                return NPY_UBYTE;
            }
            else if (value <= NPY_MAX_USHORT) {
                if (value <= NPY_MAX_SHORT) {
                    *is_small_unsigned = 1;
                }
                return NPY_USHORT;
            }
            else if (value <= NPY_MAX_UINT) {
                if (value <= NPY_MAX_INT) {
                    *is_small_unsigned = 1;
                }
                return NPY_UINT;
            }
#if NPY_SIZEOF_LONG != NPY_SIZEOF_INT && NPY_SIZEOF_LONG != NPY_SIZEOF_LONGLONG
            else if (value <= NPY_MAX_ULONG) {
                if (value <= NPY_MAX_LONG) {
                    *is_small_unsigned = 1;
                }
                return NPY_ULONG;
            }
#endif

            if (value <= NPY_MAX_LONGLONG) {
                *is_small_unsigned = 1;
            }
            break;
        }
#if NPY_SIZEOF_LONG == NPY_SIZEOF_LONGLONG
        case NPY_LONG:
#endif
        case NPY_LONGLONG: {
            npy_longlong value = *(npy_longlong *)valueptr;
            if (value >= 0) {
                return min_scalar_type_num(valueptr, NPY_ULONGLONG, is_small_unsigned);
            }
            else if (value >= NPY_MIN_BYTE) {
                return NPY_BYTE;
            }
            else if (value >= NPY_MIN_SHORT) {
                return NPY_SHORT;
            }
            else if (value >= NPY_MIN_INT) {
                return NPY_INT;
            }
#if NPY_SIZEOF_LONG != NPY_SIZEOF_INT && NPY_SIZEOF_LONG != NPY_SIZEOF_LONGLONG
            else if (value >= NPY_MIN_LONG) {
                return NPY_LONG;
            }
#endif
            break;
        }
        /*
         * Float types aren't allowed to be demoted to integer types,
         * but precision loss is allowed.
         */
        case NPY_HALF: {
            return NPY_HALF;
        }
        case NPY_FLOAT: {
            float value = *(float *)valueptr;
            if (value > -65000 && value < 65000) {
                return NPY_HALF;
            }
            break;
        }
        case NPY_DOUBLE: {
            double value = *(double *)valueptr;
            if (value > -65000 && value < 65000) {
                return NPY_HALF;
            }
            else if (value > -3.4e38 && value < 3.4e38) {
                return NPY_FLOAT;
            }
            break;
        }
        case NPY_LONGDOUBLE: {
            npy_longdouble value = *(npy_longdouble *)valueptr;
            if (value > -65000 && value < 65000) {
                return NPY_HALF;
            }
            else if (value > -3.4e38 && value < 3.4e38) {
                return NPY_FLOAT;
            }
            else if (value > -1.7e308 && value < 1.7e308) {
                return NPY_DOUBLE;
            }
            break;
        }
        /*
         * The code to demote complex to float is disabled for now,
         * as forcing complex by adding 0j is probably desireable.
         */
        case NPY_CFLOAT: {
            /*
            npy_cfloat value = *(npy_cfloat *)valueptr;
            if (value.imag == 0) {
                return min_scalar_type_num((char *)&value.real,
                                            NPY_FLOAT, is_small_unsigned);
            }
            */
            break;
        }
        case NPY_CDOUBLE: {
            npy_cdouble value = *(npy_cdouble *)valueptr;
            /*
            if (value.imag == 0) {
                return min_scalar_type_num((char *)&value.real,
                                            NPY_DOUBLE, is_small_unsigned);
            }
            */
            if (value.real > -3.4e38 && value.real < 3.4e38 &&
                     value.imag > -3.4e38 && value.imag < 3.4e38) {
                return NPY_CFLOAT;
            }
            break;
        }
        case NPY_CLONGDOUBLE: {
            npy_cdouble value = *(npy_cdouble *)valueptr;
            /*
            if (value.imag == 0) {
                return min_scalar_type_num((char *)&value.real,
                                            NPY_LONGDOUBLE, is_small_unsigned);
            }
            */
            if (value.real > -3.4e38 && value.real < 3.4e38 &&
                     value.imag > -3.4e38 && value.imag < 3.4e38) {
                return NPY_CFLOAT;
            }
            else if (value.real > -1.7e308 && value.real < 1.7e308 &&
                     value.imag > -1.7e308 && value.imag < 1.7e308) {
                return NPY_CDOUBLE;
            }
            break;
        }
    }

    return type_num;
}

/*NUMPY_API
 * If arr is a scalar (has 0 dimensions) with a built-in number data type,
 * finds the smallest type size/kind which can still represent its data.
 * Otherwise, returns the array's data type.
 *
 */
NPY_NO_EXPORT PyArray_Descr *
PyArray_MinScalarType(PyArrayObject *arr)
{
    PyArray_Descr *dtype = PyArray_DESCR(arr);
    if (PyArray_NDIM(arr) > 0 || !PyTypeNum_ISNUMBER(dtype->type_num)) {
        Py_INCREF(dtype);
        return dtype;
    }
    else {
        char *data = PyArray_BYTES(arr);
        int swap = !PyArray_ISNBO(dtype->byteorder);
        int is_small_unsigned = 0;
        /* An aligned memory buffer large enough to hold any type */
        npy_longlong value[4];
        dtype->f->copyswap(&value, data, swap, NULL);

        return PyArray_DescrFromType(
                        min_scalar_type_num((char *)&value,
                                dtype->type_num, &is_small_unsigned));

    }
}

/*
 * Provides an ordering for the dtype 'kind' character codes, to help
 * determine when to use the min_scalar_type function. This groups
 * 'kind' into boolean, integer, floating point, and everything else.
 */
static int
dtype_kind_to_simplified_ordering(char kind)
{
    switch (kind) {
        /* Boolean kind */
        case 'b':
            return 0;
        /* Unsigned int kind */
        case 'u':
        /* Signed int kind */
        case 'i':
            return 1;
        /* Float kind */
        case 'f':
        /* Complex kind */
        case 'c':
            return 2;
        /* Anything else */
        default:
            return 3;
    }
}

/*NUMPY_API
 * Produces the result type of a bunch of inputs, using the UFunc
 * type promotion rules. Use this function when you have a set of
 * input arrays, and need to determine an output array dtype.
 *
 * If all the inputs are scalars (have 0 dimensions) or the maximum "kind"
 * of the scalars is greater than the maximum "kind" of the arrays, does
 * a regular type promotion.
 *
 * Otherwise, does a type promotion on the MinScalarType
 * of all the inputs.  Data types passed directly are treated as array
 * types.
 *
 */
NPY_NO_EXPORT PyArray_Descr *
PyArray_ResultType(npy_intp narrs, PyArrayObject **arr,
                    npy_intp ndtypes, PyArray_Descr **dtypes)
{
    npy_intp i;
    int use_min_scalar = 0;
    PyArray_Descr *ret = NULL, *tmpret;
    int ret_is_small_unsigned = 0;

    /* If there's just one type, pass it through */
    if (narrs + ndtypes == 1) {
        if (narrs == 1) {
            ret = PyArray_DESCR(arr[0]);
        }
        else {
            ret = dtypes[0];
        }
        Py_INCREF(ret);
        return ret;
    }

    /*
     * Determine if there are any scalars, and if so, whether
     * the maximum "kind" of the scalars surpasses the maximum
     * "kind" of the arrays
     */
    if (narrs > 0) {
        int all_scalars, max_scalar_kind = -1, max_array_kind = -1;
        int kind;

        all_scalars = (ndtypes > 0) ? 0 : 1;

        /* Compute the maximum "kinds" and whether everything is scalar */
        for (i = 0; i < narrs; ++i) {
            if (PyArray_NDIM(arr[i]) == 0) {
                kind = dtype_kind_to_simplified_ordering(
                                    PyArray_DESCR(arr[i])->kind);
                if (kind > max_scalar_kind) {
                    max_scalar_kind = kind;
                }
            }
            else {
                all_scalars = 0;
                kind = dtype_kind_to_simplified_ordering(
                                    PyArray_DESCR(arr[i])->kind);
                if (kind > max_array_kind) {
                    max_array_kind = kind;
                }
            }
        }
        /*
         * If the max scalar kind is bigger than the max array kind,
         * finish computing the max array kind
         */
        for (i = 0; i < ndtypes; ++i) {
            kind = dtype_kind_to_simplified_ordering(dtypes[i]->kind);
            if (kind > max_array_kind) {
                max_array_kind = kind;
            }
        }

        /* Indicate whether to use the min_scalar_type function */
        if (!all_scalars && max_array_kind >= max_scalar_kind) {
            use_min_scalar = 1;
        }
    }

    /* Loop through all the types, promoting them */
    if (!use_min_scalar) {
        for (i = 0; i < narrs; ++i) {
            PyArray_Descr *tmp = PyArray_DESCR(arr[i]);
            /* Combine it with the existing type */
            if (ret == NULL) {
                ret = tmp;
                Py_INCREF(ret);
            }
            else {
                /* Only call promote if the types aren't the same dtype */
                if (tmp != ret || !PyArray_ISNBO(ret->byteorder)) {
                    tmpret = PyArray_PromoteTypes(tmp, ret);
                    Py_DECREF(ret);
                    ret = tmpret;
                    if (ret == NULL) {
                        return NULL;
                    }
                }
            }
        }

        for (i = 0; i < ndtypes; ++i) {
            PyArray_Descr *tmp = dtypes[i];
            /* Combine it with the existing type */
            if (ret == NULL) {
                ret = tmp;
                Py_INCREF(ret);
            }
            else {
                /* Only call promote if the types aren't the same dtype */
                if (tmp != ret || !PyArray_ISNBO(tmp->byteorder)) {
                    tmpret = PyArray_PromoteTypes(tmp, ret);
                    Py_DECREF(ret);
                    ret = tmpret;
                    if (ret == NULL) {
                        return NULL;
                    }
                }
            }
        }
    }
    else {
        for (i = 0; i < narrs; ++i) {
            /* Get the min scalar type for the array */
            PyArray_Descr *tmp = PyArray_DESCR(arr[i]);
            int tmp_is_small_unsigned = 0;
            /*
             * If it's a scalar, find the min scalar type. The function
             * is expanded here so that we can flag whether we've got an
             * unsigned integer which would fit an a signed integer
             * of the same size, something not exposed in the public API.
             */
            if (PyArray_NDIM(arr[i]) == 0 &&
                                PyTypeNum_ISNUMBER(tmp->type_num)) {
                char *data = PyArray_BYTES(arr[i]);
                int swap = !PyArray_ISNBO(tmp->byteorder);
                int type_num;
                /* An aligned memory buffer large enough to hold any type */
                npy_longlong value[4];
                tmp->f->copyswap(&value, data, swap, NULL);
                type_num = min_scalar_type_num((char *)&value,
                                        tmp->type_num, &tmp_is_small_unsigned);
                tmp = PyArray_DescrFromType(type_num);
                if (tmp == NULL) {
                    Py_XDECREF(ret);
                    return NULL;
                }
            }
            else {
                Py_INCREF(tmp);
            }
            /* Combine it with the existing type */
            if (ret == NULL) {
                ret = tmp;
                ret_is_small_unsigned = tmp_is_small_unsigned;
            }
            else {
#if 0
                printf("promoting type ");
                PyObject_Print(tmp, stdout, 0);
                printf(" (%d) ", tmp_is_small_unsigned);
                PyObject_Print(ret, stdout, 0);
                printf(" (%d) ", ret_is_small_unsigned);
                printf("\n");
#endif
                /* If they point to the same type, don't call promote */
                if (tmp == ret && PyArray_ISNBO(tmp->byteorder)) {
                    Py_DECREF(tmp);
                }
                else {
                    tmpret = promote_types(tmp, ret, tmp_is_small_unsigned,
                                                        ret_is_small_unsigned);
                    if (tmpret == NULL) {
                        Py_DECREF(tmp);
                        Py_DECREF(ret);
                        return NULL;
                    }
                    Py_DECREF(tmp);
                    Py_DECREF(ret);
                    ret = tmpret;
                }
                ret_is_small_unsigned = tmp_is_small_unsigned &&
                                        ret_is_small_unsigned;
            }
        }

        for (i = 0; i < ndtypes; ++i) {
            PyArray_Descr *tmp = dtypes[i];
            /* Combine it with the existing type */
            if (ret == NULL) {
                ret = tmp;
                Py_INCREF(ret);
            }
            else {
                /* Only call promote if the types aren't the same dtype */
                if (tmp != ret || !PyArray_ISNBO(tmp->byteorder)) {
                    if (ret_is_small_unsigned) {
                        tmpret = promote_types(tmp, ret, 0,
                                                ret_is_small_unsigned);
                        if (tmpret == NULL) {
                            Py_DECREF(tmp);
                            Py_DECREF(ret);
                            return NULL;
                        }
                    }
                    else {
                        tmpret = PyArray_PromoteTypes(tmp, ret);
                    }
                    Py_DECREF(ret);
                    ret = tmpret;
                    if (ret == NULL) {
                        return NULL;
                    }
                }
            }
        }
    }

    if (ret == NULL) {
        PyErr_SetString(PyExc_TypeError,
                "no arrays or types available to calculate result type");
    }

    return ret;
}

/*NUMPY_API
 * Is the typenum valid?
 */
NPY_NO_EXPORT int
PyArray_ValidType(int type)
{
    PyArray_Descr *descr;
    int res=TRUE;

    descr = PyArray_DescrFromType(type);
    if (descr == NULL) {
        res = FALSE;
    }
    Py_DECREF(descr);
    return res;
}

/* Backward compatibility only */
/* In both Zero and One

***You must free the memory once you are done with it
using PyDataMem_FREE(ptr) or you create a memory leak***

If arr is an Object array you are getting a
BORROWED reference to Zero or One.
Do not DECREF.
Please INCREF if you will be hanging on to it.

The memory for the ptr still must be freed in any case;
*/

static int
_check_object_rec(PyArray_Descr *descr)
{
    if (PyDataType_HASFIELDS(descr) && PyDataType_REFCHK(descr)) {
        PyErr_SetString(PyExc_TypeError, "Not supported for this data-type.");
        return -1;
    }
    return 0;
}

/*NUMPY_API
  Get pointer to zero of correct type for array.
*/
NPY_NO_EXPORT char *
PyArray_Zero(PyArrayObject *arr)
{
    char *zeroval;
    int ret, storeflags;
    PyObject *obj;

    if (_check_object_rec(arr->descr) < 0) {
        return NULL;
    }
    zeroval = PyDataMem_NEW(arr->descr->elsize);
    if (zeroval == NULL) {
        PyErr_SetNone(PyExc_MemoryError);
        return NULL;
    }

    obj=PyInt_FromLong((long) 0);
    if (PyArray_ISOBJECT(arr)) {
        memcpy(zeroval, &obj, sizeof(PyObject *));
        Py_DECREF(obj);
        return zeroval;
    }
    storeflags = arr->flags;
    arr->flags |= BEHAVED;
    ret = arr->descr->f->setitem(obj, zeroval, arr);
    arr->flags = storeflags;
    Py_DECREF(obj);
    if (ret < 0) {
        PyDataMem_FREE(zeroval);
        return NULL;
    }
    return zeroval;
}

/*NUMPY_API
  Get pointer to one of correct type for array
*/
NPY_NO_EXPORT char *
PyArray_One(PyArrayObject *arr)
{
    char *oneval;
    int ret, storeflags;
    PyObject *obj;

    if (_check_object_rec(arr->descr) < 0) {
        return NULL;
    }
    oneval = PyDataMem_NEW(arr->descr->elsize);
    if (oneval == NULL) {
        PyErr_SetNone(PyExc_MemoryError);
        return NULL;
    }

    obj = PyInt_FromLong((long) 1);
    if (PyArray_ISOBJECT(arr)) {
        memcpy(oneval, &obj, sizeof(PyObject *));
        Py_DECREF(obj);
        return oneval;
    }

    storeflags = arr->flags;
    arr->flags |= BEHAVED;
    ret = arr->descr->f->setitem(obj, oneval, arr);
    arr->flags = storeflags;
    Py_DECREF(obj);
    if (ret < 0) {
        PyDataMem_FREE(oneval);
        return NULL;
    }
    return oneval;
}

/* End deprecated */

/*NUMPY_API
 * Return the typecode of the array a Python object would be converted to
 */
NPY_NO_EXPORT int
PyArray_ObjectType(PyObject *op, int minimum_type)
{
    PyArray_Descr *intype;
    PyArray_Descr *outtype;
    int ret;

    intype = PyArray_DescrFromType(minimum_type);
    if (intype == NULL) {
        PyErr_Clear();
    }
    outtype = _array_find_type(op, intype, MAX_DIMS);
    ret = outtype->type_num;
    Py_DECREF(outtype);
    Py_XDECREF(intype);
    return ret;
}

/* Raises error when len(op) == 0 */

/*NUMPY_API*/
NPY_NO_EXPORT PyArrayObject **
PyArray_ConvertToCommonType(PyObject *op, int *retn)
{
    int i, n, allscalars = 0;
    PyArrayObject **mps = NULL;
    PyObject *otmp;
    PyArray_Descr *intype = NULL, *stype = NULL;
    PyArray_Descr *newtype = NULL;
    NPY_SCALARKIND scalarkind = NPY_NOSCALAR, intypekind = NPY_NOSCALAR;

    *retn = n = PySequence_Length(op);
    if (n == 0) {
        PyErr_SetString(PyExc_ValueError, "0-length sequence.");
    }
    if (PyErr_Occurred()) {
        *retn = 0;
        return NULL;
    }
    mps = (PyArrayObject **)PyDataMem_NEW(n*sizeof(PyArrayObject *));
    if (mps == NULL) {
        *retn = 0;
        return (void*)PyErr_NoMemory();
    }

    if (PyArray_Check(op)) {
        for (i = 0; i < n; i++) {
            mps[i] = (PyArrayObject *) array_big_item((PyArrayObject *)op, i);
        }
        if (!PyArray_ISCARRAY(op)) {
            for (i = 0; i < n; i++) {
                PyObject *obj;
                obj = PyArray_NewCopy(mps[i], NPY_CORDER);
                Py_DECREF(mps[i]);
                mps[i] = (PyArrayObject *)obj;
            }
        }
        return mps;
    }

    for (i = 0; i < n; i++) {
        mps[i] = NULL;
    }

    for (i = 0; i < n; i++) {
        otmp = PySequence_GetItem(op, i);
        if (!PyArray_CheckAnyScalar(otmp)) {
            newtype = PyArray_DescrFromObject(otmp, intype);
            Py_XDECREF(intype);
            if (newtype == NULL) {
                goto fail;
            }
            intype = newtype;
            intypekind = PyArray_ScalarKind(intype->type_num, NULL);
        }
        else {
            newtype = PyArray_DescrFromObject(otmp, stype);
            Py_XDECREF(stype);
            if (newtype == NULL) {
                goto fail;
            }
            stype = newtype;
            scalarkind = PyArray_ScalarKind(newtype->type_num, NULL);
            mps[i] = (PyArrayObject *)Py_None;
            Py_INCREF(Py_None);
        }
        Py_XDECREF(otmp);
    }
    if (intype == NULL) {
        /* all scalars */
        allscalars = 1;
        intype = stype;
        Py_INCREF(intype);
        for (i = 0; i < n; i++) {
            Py_XDECREF(mps[i]);
            mps[i] = NULL;
        }
    }
    else if ((stype != NULL) && (intypekind != scalarkind)) {
        /*
         * we need to upconvert to type that
         * handles both intype and stype
         * also don't forcecast the scalars.
         */
        if (!PyArray_CanCoerceScalar(stype->type_num,
                                     intype->type_num,
                                     scalarkind)) {
            newtype = PyArray_PromoteTypes(intype, stype);
            Py_XDECREF(intype);
            intype = newtype;
        }
        for (i = 0; i < n; i++) {
            Py_XDECREF(mps[i]);
            mps[i] = NULL;
        }
    }


    /* Make sure all arrays are actual array objects. */
    for (i = 0; i < n; i++) {
        int flags = CARRAY;

        if ((otmp = PySequence_GetItem(op, i)) == NULL) {
            goto fail;
        }
        if (!allscalars && ((PyObject *)(mps[i]) == Py_None)) {
            /* forcecast scalars */
            flags |= FORCECAST;
            Py_DECREF(Py_None);
        }
        Py_INCREF(intype);
        mps[i] = (PyArrayObject*)
            PyArray_FromAny(otmp, intype, 0, 0, flags, NULL);
        Py_DECREF(otmp);
        if (mps[i] == NULL) {
            goto fail;
        }
    }
    Py_DECREF(intype);
    Py_XDECREF(stype);
    return mps;

 fail:
    Py_XDECREF(intype);
    Py_XDECREF(stype);
    *retn = 0;
    for (i = 0; i < n; i++) {
        Py_XDECREF(mps[i]);
    }
    PyDataMem_FREE(mps);
    return NULL;
}
