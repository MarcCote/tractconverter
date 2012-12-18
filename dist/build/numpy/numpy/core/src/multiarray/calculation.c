#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"

#define _MULTIARRAYMODULE
#define NPY_NO_PREFIX
#include "numpy/arrayobject.h"

#include "npy_config.h"

#include "numpy/npy_3kcompat.h"

#include "common.h"
#include "number.h"

#include "calculation.h"

/* FIXME: just remove _check_axis ? */
#define _check_axis PyArray_CheckAxis
#define PyAO PyArrayObject

static double
power_of_ten(int n)
{
    static const double p10[] = {1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8};
    double ret;
    if (n < 9) {
        ret = p10[n];
    }
    else {
        ret = 1e9;
        while (n-- > 9) {
            ret *= 10.;
        }
    }
    return ret;
}

/*NUMPY_API
 * ArgMax
 */
NPY_NO_EXPORT PyObject *
PyArray_ArgMax(PyArrayObject *op, int axis, PyArrayObject *out)
{
    PyArrayObject *ap = NULL, *rp = NULL;
    PyArray_ArgFunc* arg_func;
    char *ip;
    intp *rptr;
    intp i, n, m;
    int elsize;
    int copyret = 0;
    NPY_BEGIN_THREADS_DEF;

    if ((ap=(PyAO *)_check_axis(op, &axis, 0)) == NULL) {
        return NULL;
    }
    /*
     * We need to permute the array so that axis is placed at the end.
     * And all other dimensions are shifted left.
     */
    if (axis != ap->nd-1) {
        PyArray_Dims newaxes;
        intp dims[MAX_DIMS];
        int i;

        newaxes.ptr = dims;
        newaxes.len = ap->nd;
        for (i = 0; i < axis; i++) dims[i] = i;
        for (i = axis; i < ap->nd - 1; i++) dims[i] = i + 1;
        dims[ap->nd - 1] = axis;
        op = (PyAO *)PyArray_Transpose(ap, &newaxes);
        Py_DECREF(ap);
        if (op == NULL) {
            return NULL;
        }
    }
    else {
        op = ap;
    }

    /* Will get native-byte order contiguous copy. */
    ap = (PyArrayObject *)
        PyArray_ContiguousFromAny((PyObject *)op,
                                  op->descr->type_num, 1, 0);
    Py_DECREF(op);
    if (ap == NULL) {
        return NULL;
    }
    arg_func = ap->descr->f->argmax;
    if (arg_func == NULL) {
        PyErr_SetString(PyExc_TypeError, "data type not ordered");
        goto fail;
    }
    elsize = ap->descr->elsize;
    m = ap->dimensions[ap->nd-1];
    if (m == 0) {
        PyErr_SetString(PyExc_ValueError,
                        "attempt to get argmax/argmin "\
                        "of an empty sequence");
        goto fail;
    }

    if (!out) {
        rp = (PyArrayObject *)PyArray_New(Py_TYPE(ap), ap->nd-1,
                                          ap->dimensions, PyArray_INTP,
                                          NULL, NULL, 0, 0,
                                          (PyObject *)ap);
        if (rp == NULL) {
            goto fail;
        }
    }
    else {
        if (PyArray_SIZE(out) !=
                PyArray_MultiplyList(ap->dimensions, ap->nd - 1)) {
            PyErr_SetString(PyExc_TypeError,
                            "invalid shape for output array.");
        }
        rp = (PyArrayObject *)\
            PyArray_FromArray(out,
                              PyArray_DescrFromType(PyArray_INTP),
                              NPY_CARRAY | NPY_UPDATEIFCOPY);
        if (rp == NULL) {
            goto fail;
        }
        if (rp != out) {
            copyret = 1;
        }
    }

    NPY_BEGIN_THREADS_DESCR(ap->descr);
    n = PyArray_SIZE(ap)/m;
    rptr = (intp *)rp->data;
    for (ip = ap->data, i = 0; i < n; i++, ip += elsize*m) {
        arg_func(ip, m, rptr, ap);
        rptr += 1;
    }
    NPY_END_THREADS_DESCR(ap->descr);

    Py_DECREF(ap);
    if (copyret) {
        PyArrayObject *obj;
        obj = (PyArrayObject *)rp->base;
        Py_INCREF(obj);
        Py_DECREF(rp);
        rp = obj;
    }
    return (PyObject *)rp;

 fail:
    Py_DECREF(ap);
    Py_XDECREF(rp);
    return NULL;
}

/*NUMPY_API
 * ArgMin
 */
NPY_NO_EXPORT PyObject *
PyArray_ArgMin(PyArrayObject *op, int axis, PyArrayObject *out)
{
    PyArrayObject *ap = NULL, *rp = NULL;
    PyArray_ArgFunc* arg_func;
    char *ip;
    intp *rptr;
    intp i, n, m;
    int elsize;
    NPY_BEGIN_THREADS_DEF;

    if ((ap=(PyArrayObject *)PyArray_CheckAxis(op, &axis, 0)) == NULL) {
        return NULL;
    }
    /*
     * We need to permute the array so that axis is placed at the end.
     * And all other dimensions are shifted left.
     */
    if (axis != PyArray_NDIM(ap)-1) {
        PyArray_Dims newaxes;
        intp dims[MAX_DIMS];
        int i;

        newaxes.ptr = dims;
        newaxes.len = PyArray_NDIM(ap);
        for (i = 0; i < axis; i++) dims[i] = i;
        for (i = axis; i < PyArray_NDIM(ap) - 1; i++) dims[i] = i + 1;
        dims[PyArray_NDIM(ap) - 1] = axis;
        op = (PyArrayObject *)PyArray_Transpose(ap, &newaxes);
        Py_DECREF(ap);
        if (op == NULL) {
            return NULL;
        }
    }
    else {
        op = ap;
    }

    /* Will get native-byte order contiguous copy. */
    ap = (PyArrayObject *)PyArray_ContiguousFromAny((PyObject *)op,
                                  PyArray_DESCR(op)->type_num, 1, 0);
    Py_DECREF(op);
    if (ap == NULL) {
        return NULL;
    }
    arg_func = PyArray_DESCR(ap)->f->argmin;
    if (arg_func == NULL) {
        PyErr_SetString(PyExc_TypeError, "data type not ordered");
        goto fail;
    }
    elsize = PyArray_DESCR(ap)->elsize;
    m = PyArray_DIMS(ap)[PyArray_NDIM(ap)-1];
    if (m == 0) {
        PyErr_SetString(PyExc_ValueError,
                        "attempt to get argmax/argmin "\
                        "of an empty sequence");
        goto fail;
    }

    if (!out) {
        rp = (PyArrayObject *)PyArray_New(Py_TYPE(ap), PyArray_NDIM(ap)-1,
                                          PyArray_DIMS(ap), PyArray_INTP,
                                          NULL, NULL, 0, 0,
                                          (PyObject *)ap);
        if (rp == NULL) {
            goto fail;
        }
    }
    else {
        if (PyArray_SIZE(out) !=
                PyArray_MultiplyList(PyArray_DIMS(ap), PyArray_NDIM(ap) - 1)) {
            PyErr_SetString(PyExc_TypeError,
                            "invalid shape for output array.");
        }
        rp = (PyArrayObject *)PyArray_FromArray(out,
                              PyArray_DescrFromType(PyArray_INTP),
                              NPY_CARRAY | NPY_UPDATEIFCOPY);
        if (rp == NULL) {
            goto fail;
        }
    }

    NPY_BEGIN_THREADS_DESCR(PyArray_DESCR(ap));
    n = PyArray_SIZE(ap)/m;
    rptr = (intp *)PyArray_DATA(rp);
    for (ip = PyArray_DATA(ap), i = 0; i < n; i++, ip += elsize*m) {
        arg_func(ip, m, rptr, ap);
        rptr += 1;
    }
    NPY_END_THREADS_DESCR(PyArray_DESCR(ap));

    Py_DECREF(ap);
    /* Trigger the UPDATEIFCOPY if necessary */
    if (out != NULL && out != rp) {
        Py_DECREF(rp);
        rp = out;
        Py_INCREF(rp);
    }
    return (PyObject *)rp;

 fail:
    Py_DECREF(ap);
    Py_XDECREF(rp);
    return NULL;
}

/*NUMPY_API
 * Max
 */
NPY_NO_EXPORT PyObject *
PyArray_Max(PyArrayObject *ap, int axis, PyArrayObject *out)
{
    PyArrayObject *arr;
    PyObject *ret;

    if ((arr=(PyArrayObject *)_check_axis(ap, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction(arr, n_ops.maximum, axis,
                                        arr->descr->type_num, out);
    Py_DECREF(arr);
    return ret;
}

/*NUMPY_API
 * Min
 */
NPY_NO_EXPORT PyObject *
PyArray_Min(PyArrayObject *ap, int axis, PyArrayObject *out)
{
    PyArrayObject *arr;
    PyObject *ret;

    if ((arr=(PyArrayObject *)_check_axis(ap, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction(arr, n_ops.minimum, axis,
                                        arr->descr->type_num, out);
    Py_DECREF(arr);
    return ret;
}

/*NUMPY_API
 * Ptp
 */
NPY_NO_EXPORT PyObject *
PyArray_Ptp(PyArrayObject *ap, int axis, PyArrayObject *out)
{
    PyArrayObject *arr;
    PyObject *ret;
    PyObject *obj1 = NULL, *obj2 = NULL;

    if ((arr=(PyArrayObject *)_check_axis(ap, &axis, 0)) == NULL) {
        return NULL;
    }
    obj1 = PyArray_Max(arr, axis, out);
    if (obj1 == NULL) {
        goto fail;
    }
    obj2 = PyArray_Min(arr, axis, NULL);
    if (obj2 == NULL) {
        goto fail;
    }
    Py_DECREF(arr);
    if (out) {
        ret = PyObject_CallFunction(n_ops.subtract, "OOO", out, obj2, out);
    }
    else {
        ret = PyNumber_Subtract(obj1, obj2);
    }
    Py_DECREF(obj1);
    Py_DECREF(obj2);
    return ret;

 fail:
    Py_XDECREF(arr);
    Py_XDECREF(obj1);
    Py_XDECREF(obj2);
    return NULL;
}



/*NUMPY_API
 * Set variance to 1 to by-pass square-root calculation and return variance
 * Std
 */
NPY_NO_EXPORT PyObject *
PyArray_Std(PyArrayObject *self, int axis, int rtype, PyArrayObject *out,
            int variance)
{
    return __New_PyArray_Std(self, axis, rtype, out, variance, 0);
}

NPY_NO_EXPORT PyObject *
__New_PyArray_Std(PyArrayObject *self, int axis, int rtype, PyArrayObject *out,
                  int variance, double num)
{
    PyObject *obj1 = NULL, *obj2 = NULL, *obj3 = NULL, *new = NULL;
    PyObject *ret = NULL, *newshape = NULL;
    double scl;
    int i, n;
    intp val;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    /* Compute and reshape mean */
    obj1 = PyArray_EnsureAnyArray(PyArray_Mean((PyAO *)new, axis, rtype, NULL));
    if (obj1 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    n = PyArray_NDIM(new);
    newshape = PyTuple_New(n);
    if (newshape == NULL) {
        Py_DECREF(obj1);
        Py_DECREF(new);
        return NULL;
    }
    for (i = 0; i < n; i++) {
        if (i == axis) {
            val = 1;
        }
        else {
            val = PyArray_DIM(new,i);
        }
        PyTuple_SET_ITEM(newshape, i, PyInt_FromLong((long)val));
    }
    obj2 = PyArray_Reshape((PyAO *)obj1, newshape);
    Py_DECREF(obj1);
    Py_DECREF(newshape);
    if (obj2 == NULL) {
        Py_DECREF(new);
        return NULL;
    }

    /* Compute x = x - mx */
    obj1 = PyArray_EnsureAnyArray(PyNumber_Subtract((PyObject *)new, obj2));
    Py_DECREF(obj2);
    if (obj1 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    /* Compute x * x */
    if (PyArray_ISCOMPLEX(obj1)) {
        obj3 = PyArray_Conjugate((PyAO *)obj1, NULL);
    }
    else {
        obj3 = obj1;
        Py_INCREF(obj1);
    }
    if (obj3 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    obj2 = PyArray_EnsureAnyArray                                      \
        (PyArray_GenericBinaryFunction((PyAO *)obj1, obj3, n_ops.multiply));
    Py_DECREF(obj1);
    Py_DECREF(obj3);
    if (obj2 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    if (PyArray_ISCOMPLEX(obj2)) {
        obj3 = PyObject_GetAttrString(obj2, "real");
        switch(rtype) {
        case NPY_CDOUBLE:
            rtype = NPY_DOUBLE;
            break;
        case NPY_CFLOAT:
            rtype = NPY_FLOAT;
            break;
        case NPY_CLONGDOUBLE:
            rtype = NPY_LONGDOUBLE;
            break;
        }
    }
    else {
        obj3 = obj2;
        Py_INCREF(obj2);
    }
    if (obj3 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    /* Compute add.reduce(x*x,axis) */
    obj1 = PyArray_GenericReduceFunction((PyAO *)obj3, n_ops.add,
                                         axis, rtype, NULL);
    Py_DECREF(obj3);
    Py_DECREF(obj2);
    if (obj1 == NULL) {
        Py_DECREF(new);
        return NULL;
    }
    n = PyArray_DIM(new,axis);
    Py_DECREF(new);
    scl = n - num;
    if (scl <= 0) {
        scl = NPY_NAN;
    }
    obj2 = PyFloat_FromDouble(1.0/scl);
    if (obj2 == NULL) {
        Py_DECREF(obj1);
        return NULL;
    }
    ret = PyNumber_Multiply(obj1, obj2);
    Py_DECREF(obj1);
    Py_DECREF(obj2);

    if (!variance) {
        obj1 = PyArray_EnsureAnyArray(ret);
        /* sqrt() */
        ret = PyArray_GenericUnaryFunction((PyAO *)obj1, n_ops.sqrt);
        Py_DECREF(obj1);
    }
    if (ret == NULL) {
        return NULL;
    }
    if (PyArray_CheckExact(self)) {
        goto finish;
    }
    if (PyArray_Check(self) && Py_TYPE(self) == Py_TYPE(ret)) {
        goto finish;
    }
    obj1 = PyArray_EnsureArray(ret);
    if (obj1 == NULL) {
        return NULL;
    }
    ret = PyArray_View((PyAO *)obj1, NULL, Py_TYPE(self));
    Py_DECREF(obj1);

finish:
    if (out) {
        if (PyArray_CopyAnyInto(out, (PyArrayObject *)ret) < 0) {
            Py_DECREF(ret);
            return NULL;
        }
        Py_DECREF(ret);
        Py_INCREF(out);
        return (PyObject *)out;
    }
    return ret;
}


/*NUMPY_API
 *Sum
 */
NPY_NO_EXPORT PyObject *
PyArray_Sum(PyArrayObject *self, int axis, int rtype, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction((PyAO *)new, n_ops.add, axis,
                                        rtype, out);
    Py_DECREF(new);
    return ret;
}

/*NUMPY_API
 * Prod
 */
NPY_NO_EXPORT PyObject *
PyArray_Prod(PyArrayObject *self, int axis, int rtype, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction((PyAO *)new, n_ops.multiply, axis,
                                        rtype, out);
    Py_DECREF(new);
    return ret;
}

/*NUMPY_API
 *CumSum
 */
NPY_NO_EXPORT PyObject *
PyArray_CumSum(PyArrayObject *self, int axis, int rtype, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericAccumulateFunction((PyAO *)new, n_ops.add, axis,
                                            rtype, out);
    Py_DECREF(new);
    return ret;
}

/*NUMPY_API
 * CumProd
 */
NPY_NO_EXPORT PyObject *
PyArray_CumProd(PyArrayObject *self, int axis, int rtype, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }

    ret = PyArray_GenericAccumulateFunction((PyAO *)new,
                                            n_ops.multiply, axis,
                                            rtype, out);
    Py_DECREF(new);
    return ret;
}

/*NUMPY_API
 * Round
 */
NPY_NO_EXPORT PyObject *
PyArray_Round(PyArrayObject *a, int decimals, PyArrayObject *out)
{
    PyObject *f, *ret = NULL, *tmp, *op1, *op2;
    int ret_int=0;
    PyArray_Descr *my_descr;
    if (out && (PyArray_SIZE(out) != PyArray_SIZE(a))) {
        PyErr_SetString(PyExc_ValueError,
                        "invalid output shape");
        return NULL;
    }
    if (PyArray_ISCOMPLEX(a)) {
        PyObject *part;
        PyObject *round_part;
        PyObject *new;
        int res;

        if (out) {
            new = (PyObject *)out;
            Py_INCREF(new);
        }
        else {
            new = PyArray_Copy(a);
            if (new == NULL) {
                return NULL;
            }
        }

        /* new.real = a.real.round(decimals) */
        part = PyObject_GetAttrString(new, "real");
        if (part == NULL) {
            Py_DECREF(new);
            return NULL;
        }
        part = PyArray_EnsureAnyArray(part);
        round_part = PyArray_Round((PyArrayObject *)part,
                                   decimals, NULL);
        Py_DECREF(part);
        if (round_part == NULL) {
            Py_DECREF(new);
            return NULL;
        }
        res = PyObject_SetAttrString(new, "real", round_part);
        Py_DECREF(round_part);
        if (res < 0) {
            Py_DECREF(new);
            return NULL;
        }

        /* new.imag = a.imag.round(decimals) */
        part = PyObject_GetAttrString(new, "imag");
        if (part == NULL) {
            Py_DECREF(new);
            return NULL;
        }
        part = PyArray_EnsureAnyArray(part);
        round_part = PyArray_Round((PyArrayObject *)part,
                                   decimals, NULL);
        Py_DECREF(part);
        if (round_part == NULL) {
            Py_DECREF(new);
            return NULL;
        }
        res = PyObject_SetAttrString(new, "imag", round_part);
        Py_DECREF(round_part);
        if (res < 0) {
            Py_DECREF(new);
            return NULL;
        }
        return new;
    }
    /* do the most common case first */
    if (decimals >= 0) {
        if (PyArray_ISINTEGER(a)) {
            if (out) {
                if (PyArray_CopyAnyInto(out, a) < 0) {
                    return NULL;
                }
                Py_INCREF(out);
                return (PyObject *)out;
            }
            else {
                Py_INCREF(a);
                return (PyObject *)a;
            }
        }
        if (decimals == 0) {
            if (out) {
                return PyObject_CallFunction(n_ops.rint, "OO", a, out);
            }
            return PyObject_CallFunction(n_ops.rint, "O", a);
        }
        op1 = n_ops.multiply;
        op2 = n_ops.true_divide;
    }
    else {
        op1 = n_ops.true_divide;
        op2 = n_ops.multiply;
        decimals = -decimals;
    }
    if (!out) {
        if (PyArray_ISINTEGER(a)) {
            ret_int = 1;
            my_descr = PyArray_DescrFromType(NPY_DOUBLE);
        }
        else {
            Py_INCREF(a->descr);
            my_descr = a->descr;
        }
        out = (PyArrayObject *)PyArray_Empty(a->nd, a->dimensions,
                                             my_descr,
                                             PyArray_ISFORTRAN(a));
        if (out == NULL) {
            return NULL;
        }
    }
    else {
        Py_INCREF(out);
    }
    f = PyFloat_FromDouble(power_of_ten(decimals));
    if (f == NULL) {
        return NULL;
    }
    ret = PyObject_CallFunction(op1, "OOO", a, f, out);
    if (ret == NULL) {
        goto finish;
    }
    tmp = PyObject_CallFunction(n_ops.rint, "OO", ret, ret);
    if (tmp == NULL) {
        Py_DECREF(ret);
        ret = NULL;
        goto finish;
    }
    Py_DECREF(tmp);
    tmp = PyObject_CallFunction(op2, "OOO", ret, f, ret);
    if (tmp == NULL) {
        Py_DECREF(ret);
        ret = NULL;
        goto finish;
    }
    Py_DECREF(tmp);

 finish:
    Py_DECREF(f);
    Py_DECREF(out);
    if (ret_int) {
        Py_INCREF(a->descr);
        tmp = PyArray_CastToType((PyArrayObject *)ret,
                                 a->descr, PyArray_ISFORTRAN(a));
        Py_DECREF(ret);
        return tmp;
    }
    return ret;
}


/*NUMPY_API
 * Mean
 */
NPY_NO_EXPORT PyObject *
PyArray_Mean(PyArrayObject *self, int axis, int rtype, PyArrayObject *out)
{
    PyObject *obj1 = NULL, *obj2 = NULL;
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    obj1 = PyArray_GenericReduceFunction((PyAO *)new, n_ops.add, axis,
                                         rtype, out);
    obj2 = PyFloat_FromDouble((double) PyArray_DIM(new,axis));
    Py_DECREF(new);
    if (obj1 == NULL || obj2 == NULL) {
        Py_XDECREF(obj1);
        Py_XDECREF(obj2);
        return NULL;
    }
    if (!out) {
#if defined(NPY_PY3K)
        ret = PyNumber_TrueDivide(obj1, obj2);
#else
        ret = PyNumber_Divide(obj1, obj2);
#endif
    }
    else {
        ret = PyObject_CallFunction(n_ops.divide, "OOO", out, obj2, out);
    }
    Py_DECREF(obj1);
    Py_DECREF(obj2);
    return ret;
}

/*NUMPY_API
 * Any
 */
NPY_NO_EXPORT PyObject *
PyArray_Any(PyArrayObject *self, int axis, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction((PyAO *)new,
                                        n_ops.logical_or, axis,
                                        PyArray_BOOL, out);
    Py_DECREF(new);
    return ret;
}

/*NUMPY_API
 * All
 */
NPY_NO_EXPORT PyObject *
PyArray_All(PyArrayObject *self, int axis, PyArrayObject *out)
{
    PyObject *new, *ret;

    if ((new = _check_axis(self, &axis, 0)) == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction((PyAO *)new,
                                        n_ops.logical_and, axis,
                                        PyArray_BOOL, out);
    Py_DECREF(new);
    return ret;
}


static PyObject *
_GenericBinaryOutFunction(PyArrayObject *m1, PyObject *m2, PyArrayObject *out,
                          PyObject *op)
{
    if (out == NULL) {
        return PyObject_CallFunction(op, "OO", m1, m2);
    }
    else {
        return PyObject_CallFunction(op, "OOO", m1, m2, out);
    }
}

static PyObject *
_slow_array_clip(PyArrayObject *self, PyObject *min, PyObject *max, PyArrayObject *out)
{
    PyObject *res1=NULL, *res2=NULL;

    if (max != NULL) {
        res1 = _GenericBinaryOutFunction(self, max, out, n_ops.minimum);
        if (res1 == NULL) {
            return NULL;
        }
    }
    else {
        res1 = (PyObject *)self;
        Py_INCREF(res1);
    }

    if (min != NULL) {
        res2 = _GenericBinaryOutFunction((PyArrayObject *)res1,
                                         min, out, n_ops.maximum);
        if (res2 == NULL) {
            Py_XDECREF(res1);
            return NULL;
        }
    }
    else {
        res2 = res1;
        Py_INCREF(res2);
    }
    Py_DECREF(res1);
    return res2;
}

/*NUMPY_API
 * Clip
 */
NPY_NO_EXPORT PyObject *
PyArray_Clip(PyArrayObject *self, PyObject *min, PyObject *max, PyArrayObject *out)
{
    PyArray_FastClipFunc *func;
    int outgood = 0, ingood = 0;
    PyArrayObject *maxa = NULL;
    PyArrayObject *mina = NULL;
    PyArrayObject *newout = NULL, *newin = NULL;
    PyArray_Descr *indescr, *newdescr;
    char *max_data, *min_data;
    PyObject *zero;

    if ((max == NULL) && (min == NULL)) {
        PyErr_SetString(PyExc_ValueError, "array_clip: must set either max "\
                        "or min");
        return NULL;
    }

    func = self->descr->f->fastclip;
    if (func == NULL || (min != NULL && !PyArray_CheckAnyScalar(min)) ||
        (max != NULL && !PyArray_CheckAnyScalar(max))) {
        return _slow_array_clip(self, min, max, out);
    }
    /* Use the fast scalar clip function */

    /* First we need to figure out the correct type */
    indescr = NULL;
    if (min != NULL) {
        indescr = PyArray_DescrFromObject(min, NULL);
        if (indescr == NULL) {
            return NULL;
        }
    }
    if (max != NULL) {
        newdescr = PyArray_DescrFromObject(max, indescr);
        Py_XDECREF(indescr);
        if (newdescr == NULL) {
            return NULL;
        }
    }
    else {
        /* Steal the reference */
        newdescr = indescr;
    }


    /*
     * Use the scalar descriptor only if it is of a bigger
     * KIND than the input array (and then find the
     * type that matches both).
     */
    if (PyArray_ScalarKind(newdescr->type_num, NULL) >
        PyArray_ScalarKind(self->descr->type_num, NULL)) {
        indescr = PyArray_PromoteTypes(newdescr, self->descr);
        func = indescr->f->fastclip;
        if (func == NULL) {
            return _slow_array_clip(self, min, max, out);
        }
    }
    else {
        indescr = self->descr;
        Py_INCREF(indescr);
    }
    Py_DECREF(newdescr);

    if (!PyDataType_ISNOTSWAPPED(indescr)) {
        PyArray_Descr *descr2;
        descr2 = PyArray_DescrNewByteorder(indescr, '=');
        Py_DECREF(indescr);
        if (descr2 == NULL) {
            goto fail;
        }
        indescr = descr2;
    }

    /* Convert max to an array */
    if (max != NULL) {
        maxa = (NPY_AO *)PyArray_FromAny(max, indescr, 0, 0,
                                         NPY_DEFAULT, NULL);
        if (maxa == NULL) {
            return NULL;
        }
    }
    else {
        /* Side-effect of PyArray_FromAny */
        Py_DECREF(indescr);
    }

    /*
     * If we are unsigned, then make sure min is not < 0
     * This is to match the behavior of _slow_array_clip
     *
     * We allow min and max to go beyond the limits
     * for other data-types in which case they
     * are interpreted as their modular counterparts.
    */
    if (min != NULL) {
        if (PyArray_ISUNSIGNED(self)) {
            int cmp;
            zero = PyInt_FromLong(0);
            cmp = PyObject_RichCompareBool(min, zero, Py_LT);
            if (cmp == -1) {
                Py_DECREF(zero);
                goto fail;
            }
            if (cmp == 1) {
                min = zero;
            }
            else {
                Py_DECREF(zero);
                Py_INCREF(min);
            }
        }
        else {
            Py_INCREF(min);
        }

        /* Convert min to an array */
        Py_INCREF(indescr);
        mina = (NPY_AO *)PyArray_FromAny(min, indescr, 0, 0,
                                         NPY_DEFAULT, NULL);
        Py_DECREF(min);
        if (mina == NULL) {
            goto fail;
        }
    }


    /*
     * Check to see if input is single-segment, aligned,
     * and in native byteorder
     */
    if (PyArray_ISONESEGMENT(self) && PyArray_CHKFLAGS(self, ALIGNED) &&
        PyArray_ISNOTSWAPPED(self) && (self->descr == indescr)) {
        ingood = 1;
    }
    if (!ingood) {
        int flags;

        if (PyArray_ISFORTRAN(self)) {
            flags = NPY_FARRAY;
        }
        else {
            flags = NPY_CARRAY;
        }
        Py_INCREF(indescr);
        newin = (NPY_AO *)PyArray_FromArray(self, indescr, flags);
        if (newin == NULL) {
            goto fail;
        }
    }
    else {
        newin = self;
        Py_INCREF(newin);
    }

    /*
     * At this point, newin is a single-segment, aligned, and correct
     * byte-order array of the correct type
     *
     * if ingood == 0, then it is a copy, otherwise,
     * it is the original input.
     */

    /*
     * If we have already made a copy of the data, then use
     * that as the output array
     */
    if (out == NULL && !ingood) {
        out = newin;
    }

    /*
     * Now, we know newin is a usable array for fastclip,
     * we need to make sure the output array is available
     * and usable
     */
    if (out == NULL) {
        Py_INCREF(indescr);
        out = (NPY_AO*)PyArray_NewFromDescr(Py_TYPE(self),
                                            indescr, self->nd,
                                            self->dimensions,
                                            NULL, NULL,
                                            PyArray_ISFORTRAN(self),
                                            (PyObject *)self);
        if (out == NULL) {
            goto fail;
        }
        outgood = 1;
    }
    else Py_INCREF(out);
    /* Input is good at this point */
    if (out == newin) {
        outgood = 1;
    }
    if (!outgood && PyArray_ISONESEGMENT(out) &&
        PyArray_CHKFLAGS(out, ALIGNED) && PyArray_ISNOTSWAPPED(out) &&
        PyArray_EquivTypes(out->descr, indescr)) {
        outgood = 1;
    }

    /*
     * Do we still not have a suitable output array?
     * Create one, now
     */
    if (!outgood) {
        int oflags;
        if (PyArray_ISFORTRAN(out))
            oflags = NPY_FARRAY;
        else
            oflags = NPY_CARRAY;
        oflags |= NPY_UPDATEIFCOPY | NPY_FORCECAST;
        Py_INCREF(indescr);
        newout = (NPY_AO*)PyArray_FromArray(out, indescr, oflags);
        if (newout == NULL) {
            goto fail;
        }
    }
    else {
        newout = out;
        Py_INCREF(newout);
    }

    /* make sure the shape of the output array is the same */
    if (!PyArray_SAMESHAPE(newin, newout)) {
        PyErr_SetString(PyExc_ValueError, "clip: Output array must have the"
                        "same shape as the input.");
        goto fail;
    }
    if (newout->data != newin->data) {
        memcpy(newout->data, newin->data, PyArray_NBYTES(newin));
    }

    /* Now we can call the fast-clip function */
    min_data = max_data = NULL;
    if (mina != NULL) {
        min_data = mina->data;
    }
    if (maxa != NULL) {
        max_data = maxa->data;
    }
    func(newin->data, PyArray_SIZE(newin), min_data, max_data, newout->data);

    /* Clean up temporary variables */
    Py_XDECREF(mina);
    Py_XDECREF(maxa);
    Py_DECREF(newin);
    /* Copy back into out if out was not already a nice array. */
    Py_DECREF(newout);
    return (PyObject *)out;

 fail:
    Py_XDECREF(maxa);
    Py_XDECREF(mina);
    Py_XDECREF(newin);
    PyArray_XDECREF_ERR(newout);
    return NULL;
}


/*NUMPY_API
 * Conjugate
 */
NPY_NO_EXPORT PyObject *
PyArray_Conjugate(PyArrayObject *self, PyArrayObject *out)
{
    if (PyArray_ISCOMPLEX(self)) {
        if (out == NULL) {
            return PyArray_GenericUnaryFunction(self,
                                                n_ops.conjugate);
        }
        else {
            return PyArray_GenericBinaryFunction(self,
                                                 (PyObject *)out,
                                                 n_ops.conjugate);
        }
    }
    else {
        PyArrayObject *ret;
        if (out) {
            if (PyArray_CopyAnyInto(out, self) < 0) {
                return NULL;
            }
            ret = out;
        }
        else {
            ret = self;
        }
        Py_INCREF(ret);
        return (PyObject *)ret;
    }
}

/*NUMPY_API
 * Trace
 */
NPY_NO_EXPORT PyObject *
PyArray_Trace(PyArrayObject *self, int offset, int axis1, int axis2,
              int rtype, PyArrayObject *out)
{
    PyObject *diag = NULL, *ret = NULL;

    diag = PyArray_Diagonal(self, offset, axis1, axis2);
    if (diag == NULL) {
        return NULL;
    }
    ret = PyArray_GenericReduceFunction((PyAO *)diag, n_ops.add, -1, rtype, out);
    Py_DECREF(diag);
    return ret;
}
