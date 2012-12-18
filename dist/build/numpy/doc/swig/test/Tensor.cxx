#include <stdlib.h>
#include <math.h>
#include <iostream>
#include "Tensor.h"

// The following macro defines a family of functions that work with 3D
// arrays with the forms
//
//     TYPE SNAMENorm(   TYPE tensor[2][2][2]);
//     TYPE SNAMEMax(    TYPE * tensor, int rows, int cols, int num);
//     TYPE SNAMEMin(    int rows, int cols, int num, TYPE * tensor);
//     void SNAMEScale(  TYPE tensor[3][3][3]);
//     void SNAMEFloor(  TYPE * array,  int rows, int cols, int num, TYPE floor);
//     void SNAMECeil(   int rows, int cols, int num, TYPE * array, TYPE ceil);
//     void SNAMELUSplit(TYPE in[2][2][2], TYPE lower[2][2][2], TYPE upper[2][2][2]);
//
// for any specified type TYPE (for example: short, unsigned int, long
// long, etc.) with given short name SNAME (for example: short, uint,
// longLong, etc.).  The macro is then expanded for the given
// TYPE/SNAME pairs.  The resulting functions are for testing numpy
// interfaces, respectively, for:
//
//  * 3D input arrays, hard-coded length
//  * 3D input arrays
//  * 3D input arrays, data last
//  * 3D in-place arrays, hard-coded lengths
//  * 3D in-place arrays
//  * 3D in-place arrays, data last
//  * 3D argout arrays, hard-coded length
//
#define TEST_FUNCS(TYPE, SNAME) \
\
TYPE SNAME ## Norm(TYPE tensor[2][2][2]) {	     \
  double result = 0;				     \
  for (int k=0; k<2; ++k)			     \
    for (int j=0; j<2; ++j)			     \
      for (int i=0; i<2; ++i)			     \
	result += tensor[i][j][k] * tensor[i][j][k]; \
  return (TYPE)sqrt(result/8);			     \
}						     \
\
TYPE SNAME ## Max(TYPE * tensor, int rows, int cols, int num) { \
  int i, j, k, index;						\
  TYPE result = tensor[0];					\
  for (k=0; k<num; ++k) {					\
    for (j=0; j<cols; ++j) {					\
      for (i=0; i<rows; ++i) {					\
	index = k*rows*cols + j*rows + i;			\
	if (tensor[index] > result) result = tensor[index];	\
      }								\
    }								\
  }								\
  return result;						\
}								\
\
TYPE SNAME ## Min(int rows, int cols, int num, TYPE * tensor) {	\
  int i, j, k, index;						\
  TYPE result = tensor[0];					\
  for (k=0; k<num; ++k) {					\
    for (j=0; j<cols; ++j) {					\
      for (i=0; i<rows; ++i) {					\
	index = k*rows*cols + j*rows + i;			\
	if (tensor[index] < result) result = tensor[index];	\
      }								\
    }								\
  }								\
  return result;						\
}								\
\
void SNAME ## Scale(TYPE array[3][3][3], TYPE val) { \
  for (int i=0; i<3; ++i)			     \
    for (int j=0; j<3; ++j)			     \
      for (int k=0; k<3; ++k)			     \
	array[i][j][k] *= val;			     \
}						     \
\
void SNAME ## Floor(TYPE * array, int rows, int cols, int num, TYPE floor) { \
  int i, j, k, index;							     \
  for (k=0; k<num; ++k) {						     \
    for (j=0; j<cols; ++j) {						     \
      for (i=0; i<rows; ++i) {						     \
	index = k*cols*rows + j*rows + i;				     \
	if (array[index] < floor) array[index] = floor;			     \
      }									     \
    }									     \
  }									     \
}									     \
\
void SNAME ## Ceil(int rows, int cols, int num, TYPE * array, TYPE ceil) { \
  int i, j, k, index;							   \
  for (k=0; k<num; ++k) {						   \
    for (j=0; j<cols; ++j) {						   \
      for (i=0; i<rows; ++i) {						   \
	index = j*rows + i;						   \
	if (array[index] > ceil) array[index] = ceil;			   \
      }									   \
    }									   \
  }									   \
}									   \
\
void SNAME ## LUSplit(TYPE tensor[2][2][2], TYPE lower[2][2][2], \
		      TYPE upper[2][2][2]) {			 \
  int sum;							 \
  for (int k=0; k<2; ++k) {					 \
    for (int j=0; j<2; ++j) {					 \
      for (int i=0; i<2; ++i) {					 \
	sum = i + j + k;					 \
	if (sum < 2) {						 \
	  lower[i][j][k] = tensor[i][j][k];			 \
	  upper[i][j][k] = 0;					 \
	} else {						 \
	  upper[i][j][k] = tensor[i][j][k];			 \
	  lower[i][j][k] = 0;					 \
	}							 \
      }								 \
    }								 \
  }								 \
}

TEST_FUNCS(signed char       , schar    )
TEST_FUNCS(unsigned char     , uchar    )
TEST_FUNCS(short             , short    )
TEST_FUNCS(unsigned short    , ushort   )
TEST_FUNCS(int               , int      )
TEST_FUNCS(unsigned int      , uint     )
TEST_FUNCS(long              , long     )
TEST_FUNCS(unsigned long     , ulong    )
TEST_FUNCS(long long         , longLong )
TEST_FUNCS(unsigned long long, ulongLong)
TEST_FUNCS(float             , float    )
TEST_FUNCS(double            , double   )
