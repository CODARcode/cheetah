#include <regex>
#include <fstream>
#include <cstring>
#include <iostream>
#include "mgard_local.h"

void MGARD_Init(const std::string & config_file, MGARD_PARAMETERS * parameters)
{
  std::ifstream in(config_file);
  std::string line;
  std::regex e1 ("tolerance");
  std::regex e2 (".*\\s*=\\s*(.+)");
  std::smatch m;
  while(std::getline(in, line))
    {
      if(std::regex_search(line, m, e1))
        {
          parameters->tolerance = std::stod(regex_replace(line, e2, "$1"));
        }
    }
  in.close();
}


void MGARD_Compress_Decompress(double *indata, std::vector<std::size_t> &shape,
			     MGARD_PARAMETERS *params, MGARD_OUTPUT *out)
{
  std::size_t inN = shape[0] * shape[1] * shape[2];
  std::size_t inSize = inN * sizeof(double);
  double *tmp = (double*)malloc(inSize);//is it really necessary?
  memcpy ( tmp, indata, inSize );
  int nfib = 1;
  out->compressed = (unsigned char*)mgard_compress(1, tmp, &out->compressed_size, shape[2],
				   shape[1], shape[0], &params->tolerance); // why &params->tolerance?
  out->decompressed = (double*)mgard_decompress(1, out->compressed, out->compressed_size,
					       shape[2], shape[1], shape[0]);
  free(tmp);
}