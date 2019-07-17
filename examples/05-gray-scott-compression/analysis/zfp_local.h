#include <zfp.h>

struct ZFP_PARAMETERS
{
  double tolerance;
};

struct ZFP_OUTPUT
{
  void *compressed;
  void *decompressed;
  std::size_t compressed_size;
};


void ZFP_Init(const std::string & config_file, ZFP_PARAMETERS * parameters);


void ZFP_Compress_Decompress(double *indata,  std::vector<std::size_t> &shape,
			     ZFP_PARAMETERS *params, ZFP_OUTPUT *out,
			     long *compressT, long *decompressT );
