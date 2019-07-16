extern "C" {
#include "mgard_capi.h"
}
  
struct MGARD_PARAMETERS
{
  double tolerance;
};

struct MGARD_OUTPUT
{
  unsigned char *compressed = nullptr;
  double *decompressed = nullptr;
  int compressed_size;
};

void MGARD_Init(const std::string & config_file, MGARD_PARAMETERS * parameters);

void MGARD_Compress_Decompress(double *indata, std::vector<std::size_t> &shape,
			       MGARD_PARAMETERS *params, MGARD_OUTPUT *out);
