#include "zchecker.h"
#include "ftk_3D_interface.h"


double * z_check_mgard(int stepAnalysis, std::vector<double>& u, const std::string &solution,
		       const std::vector<std::size_t>& shape)
{
  std::string tstr = std::to_string(stepAnalysis);
  char varName[1024];
  strcpy(varName, tstr.c_str());
  ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(),
					       0, 0, shape[2], shape[1], shape[1]);
  assert(u.size() == shape[0]*shape[1]*shape[2]);

  /* Is this necessary? MGARD README suggests that tmp would be blown away
     after usage, might corrupt u-vector to do it to u.data()
  */
  double * tmp = (double*)malloc(u.size()*sizeof(double));
  for(int i = 0; i < u.size(); ++i) tmp[i] = u[i];
  // necessary?
  
  double tolerance = 1.e-8; // pass it as an argument to function and exe
  int outSize;
  int nfib=1;
  /* Is the order of shapes correct? Is nfib the 3rd dim? */
  unsigned char *bytes = mgard_compress(1, tmp, &outSize, shape[2],
					shape[1], shape[0], &tolerance);
  std::cout << "stepAnalysis=" << stepAnalysis << std::endl;
  std::cout << "inSize  = " << u.size()*sizeof(double) << std::endl; 
  std::cout << "outSize = " << outSize << std::endl;
  std::cout.flush();
  
  char s[1024];
  strcpy(s, solution.c_str());
  ZC_CompareData* compareResult = ZC_endCmpr(dataProperty, s, outSize);

  ZC_startDec();

  double * decData = (double*)mgard_decompress(1, bytes, outSize,
					       shape[2], shape[1], shape[0]);
  ZC_endDec(compareResult, decData);
  ZC_printCompressionResult(compareResult);
  
  freeDataProperty(dataProperty);
  freeCompareResult(compareResult);
  free(bytes);
  //free(decData);
  free(tmp);
  return decData;
}

// pass shape, tolerance
double * z_check_zfp(int stepAnalysis, std::vector<double>& u, const std::string &solution)
{
  std::string tstr = std::to_string(stepAnalysis);
  char varName[1024];
  strcpy(varName, tstr.c_str());
  ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(),
					       0, 0, 0, 0, u.size());

  double tolerance = 1.e-8;
  zfp_type type = zfp_type_double;
  zfp_field* field = zfp_field_1d(u.data(), type, u.size());
  zfp_stream* zfp = zfp_stream_open(NULL);
  zfp_stream_set_accuracy(zfp, tolerance);
  size_t bufsize = zfp_stream_maximum_size(zfp, field);
  void* buffer = malloc(bufsize);
  bitstream* stream = stream_open(buffer, bufsize);
  zfp_stream_set_bit_stream(zfp, stream);
  zfp_stream_rewind(zfp);
  size_t outSize = zfp_compress(zfp, field);
  std::cout << "inSize  = " << u.size()*sizeof(double) << std::endl; 
  std::cout << "outSize = " << outSize << std::endl;
  std::cout.flush();
  
  char s[1024];
  strcpy(s, solution.c_str());
  ZC_CompareData* compareResult = ZC_endCmpr(dataProperty, s, outSize);

  ZC_startDec();
  // should it be allocated or is it down inside decompress?
  void* decData = malloc(u.size()*sizeof(double));
  zfp_field* field_dec = zfp_field_1d(decData, type, u.size());
  zfp_stream_rewind(zfp);
  size_t size = zfp_decompress(zfp, field_dec);

  ZC_endDec(compareResult, decData);
  ZC_printCompressionResult(compareResult);

  freeDataProperty(dataProperty);
  freeCompareResult(compareResult);
  free(buffer);
  //free(decData);
  return (double*)decData;
}

double* z_check_sz(int stepAnalysis, std::vector<double>& u,
				   const std::string &solution,
				   const std::vector<std::size_t>& shape)
{
  std::string tstr = std::to_string(stepAnalysis);
  char varName[1024];
  strcpy(varName, tstr.c_str());
  ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(),
					       0, 0, shape[2], shape[1], shape[0]);	
  size_t outSize;
  
  unsigned char *bytes = SZ_compress(SZ_DOUBLE, u.data(), &outSize,
				     0, 0, shape[2], shape[1], shape[0]);
  std::cout << "outSize=" << outSize << std::endl;
  std::cout.flush();
  
  char s[1024];
  strcpy(s, solution.c_str());
  ZC_CompareData* compareResult = ZC_endCmpr(dataProperty, s, outSize);
  
  ZC_startDec();
  double *decData = (double*)SZ_decompress(SZ_DOUBLE, bytes, outSize,
					   0, 0, shape[2], shape[1], shape[0]);
  
  ZC_endDec(compareResult, decData);
  ZC_printCompressionResult(compareResult);
  
  freeDataProperty(dataProperty);
  freeCompareResult(compareResult);
  free(bytes);
  //free(decData);
  return decData;
}



