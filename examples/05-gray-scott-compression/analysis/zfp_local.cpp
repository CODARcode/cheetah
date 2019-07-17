#include <regex>
#include <fstream>
#include <cassert>
#include <iostream>
#include <chrono>
#include "zfp_local.h"

void ZFP_Init(const std::string & config_file, ZFP_PARAMETERS * parameters)
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

void ZFP_Compress_Decompress(double *indata, std::vector<std::size_t> &shape,
			     ZFP_PARAMETERS *params, ZFP_OUTPUT *out,
			     long *compressT, long *decompressT)
{
  std::size_t insize = shape[0]*shape[1]*shape[2];
  zfp_type type = zfp_type_double;

  auto start = std::chrono::steady_clock::now();  
  zfp_field *field = zfp_field_1d(indata, type, insize);
  zfp_stream* zfp = zfp_stream_open(NULL);
  zfp_stream_set_accuracy(zfp, params->tolerance);
  size_t bufsize = zfp_stream_maximum_size(zfp, field);
  out->compressed = malloc(bufsize);
  bitstream* stream = stream_open(out->compressed, bufsize);
  zfp_stream_set_bit_stream(zfp, stream);
  zfp_stream_rewind(zfp);
  out->compressed_size = zfp_compress(zfp, field);
  auto end = std::chrono::steady_clock::now();
  *compressT = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();  

  start = std::chrono::steady_clock::now();    
  out->decompressed = malloc(insize*sizeof(double));
  zfp_field* field_dec = zfp_field_1d(out->decompressed, type, insize);
  zfp_stream_rewind(zfp);
  std::size_t size = zfp_decompress(zfp, field_dec);
  end = std::chrono::steady_clock::now();
  *decompressT = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();  
}
