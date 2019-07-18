#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <mpi.h>
#include <adios2.h>
#include "sz_local.h"
#include "mgard_local.h"
#include "zfp_local.h"

void usage()
{
  std::cout << "mpirun -n 1 compress <compressor> <input_filename>"
	    << "  <original_output_file_name> <compressed_output_filename>"
	    << "  <decompressed_output_filename>" << std::endl;
  std::cout << "where <compressor> can be: 1 (SZ), 2 (ZFP), 3 (MGARD)" << std::endl;
}

int main(int argc, char **argv)
{
  int provided;
  MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
  int rank, comm_size, wrank;

  MPI_Comm_rank(MPI_COMM_WORLD, &wrank);
  const unsigned int color = 2;
  MPI_Comm comm;
  MPI_Comm_split(MPI_COMM_WORLD, color, wrank, &comm);

  MPI_Comm_rank(comm, &rank);
  MPI_Comm_size(comm, &comm_size);

  if(comm_size != 1)
    {
      if(!rank)
	{
	  std::cerr << "comm_size = " << comm_size << std::endl;
	  std::cerr << "compress currently supports only MPI jobs with one rank" << std::endl;
	}
      MPI_Finalize();
      return 1;
    }
  
  if(argc != 6)
    {
      usage();
      MPI_Finalize();
      return 1;
    }

  int compressor = std::stoi(argv[1]);
  std::string in_filename = argv[2];
  std::string out_original_filename = argv[3];
  std::string out_compressed_filename = argv[4];
  std::string out_decompressed_filename = argv[5];

  ZFP_PARAMETERS zfp_parameters;
  MGARD_PARAMETERS mgard_parameters;
  ZFP_OUTPUT zfp_output_U;
  ZFP_OUTPUT zfp_output_V;
  MGARD_OUTPUT mgard_output_U;
  MGARD_OUTPUT mgard_output_V;

  switch(compressor)
    {
    case 1:
      std::cout << "SZ" << std::endl;
      SZ_Init("sz.config");
      break;
    case 2:
      std::cout << "ZFP" << std::endl;
      ZFP_Init("zfp.config", &zfp_parameters);
      std::cout << "zfp_parameters.tolerance = " << zfp_parameters.tolerance << std::endl;
      break;
    case 3:
      std::cout << "MGARD" << std::endl;
      MGARD_Init("mgard.config", &mgard_parameters);
      break;
    default:
      usage();
      MPI_Finalize();
      return 1;
    }


  std::size_t u_global_size, v_global_size;
  std::size_t u_local_size, v_local_size;
  std::vector<double> u;
  std::vector<double> v;
  
  adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);

  adios2::IO reader_io = ad.DeclareIO("SimulationOutput");
  adios2::IO writer_compressed_io = ad.DeclareIO("CompressedOutput");
  adios2::IO writer_decompressed_io = ad.DeclareIO("DecompressedOutput");  
  adios2::IO writer_original_io = ad.DeclareIO("OriginalOutput");

  writer_compressed_io.DefineAttribute<int>("compressor", compressor);
  
  adios2::Engine reader =
    reader_io.Open(in_filename,
		   adios2::Mode::Read, comm);
  adios2::Engine writer_original =
    writer_original_io.Open(out_original_filename,
			    adios2::Mode::Write, comm);
  adios2::Engine writer_compressed =
    writer_compressed_io.Open(out_compressed_filename,
			      adios2::Mode::Write, comm);
  adios2::Engine writer_decompressed =
    writer_decompressed_io.Open(out_decompressed_filename,
				adios2::Mode::Write, comm);  

  adios2::Variable<double> var_u_in, var_v_in;
  adios2::Variable<int> var_step_in;
  
  adios2::Variable<double> var_u_original_out, var_v_original_out;
  adios2::Variable<unsigned char> var_u_compressed_out, var_v_compressed_out;
  adios2::Variable<double> var_u_decompressed_out, var_v_decompressed_out;  

  adios2::Variable<double>  var_u_compress_ratio, var_v_compress_ratio;
  adios2::Variable<long>  var_u_compress_time, var_v_compress_time;
  adios2::Variable<long>  var_u_decompress_time, var_v_decompress_time;    
  
  adios2::Variable<int> var_u_size;
  adios2::Variable<int> var_v_size;
    
  std::vector<std::size_t> shape;
  bool firstStep = true;
  
  int stepAnalysis = 0;
  while(true)
    {
      std::cout <<  "stepAnalysis = " << stepAnalysis << std::endl;
      std::cout.flush();
      adios2::StepStatus read_status = reader.BeginStep();


        if (read_status == adios2::StepStatus::NotReady)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            continue;
        }
        else if (read_status != adios2::StepStatus::OK)
        {
            break;
        }
	
        int stepSimOut = reader.CurrentStep();
        var_u_in = reader_io.InquireVariable<double>("U");
        var_v_in = reader_io.InquireVariable<double>("V");
        var_step_in = reader_io.InquireVariable<int>("step");
        shape = var_u_in.Shape();

        u_global_size = shape[0] * shape[1] * shape[2];
        u_local_size  = u_global_size/comm_size;
        v_global_size = shape[0] * shape[1] * shape[2];
        v_local_size  = v_global_size/comm_size;

        size_t count1 = shape[0]/comm_size;
        size_t start1 = count1 * rank;
        if (rank == comm_size-1) {
            count1 = shape[0] - count1 * (comm_size - 1);
        }

	std::vector<std::size_t> local_shape = {count1, shape[1], shape[2]};
	
        var_u_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1, 0, 0},
                    {count1, shape[1], shape[2]}));
        var_v_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1, 0, 0},
                    {count1, shape[1], shape[2]}));

	reader.Get<double>(var_u_in, u);
        reader.Get<double>(var_v_in, v);
        reader.EndStep();


	if (firstStep)
	  {
	    var_u_original_out =
	      writer_original_io.DefineVariable<double> ("U/original",
							 { shape[0], shape[1], shape[2] },
							 { start1, 0, 0 },
							 { count1, shape[1], shape[2] } );
	    var_v_original_out =
	      writer_original_io.DefineVariable<double> ("V/original",
							 { shape[0], shape[1], shape[2] },
							 { start1, 0, 0 },
							 { count1, shape[1], shape[2] } );
	    var_u_size =
	      writer_compressed_io.DefineVariable<int>("U/size", {adios2::LocalValueDim});
	    var_v_size =
	      writer_compressed_io.DefineVariable<int>("V/size", {adios2::LocalValueDim});

	    var_u_compressed_out =
	      writer_compressed_io.DefineVariable<unsigned char> ("U/compressed",
								  { 1}, { 0}, { 1} );
	    var_v_compressed_out =
	      writer_compressed_io.DefineVariable<unsigned char> ("V/compressed",
								  { 1}, { 0}, { 1} );
	    var_u_decompressed_out =
	      writer_decompressed_io.DefineVariable<double> ("U/decompressed",
							     { shape[0], shape[1], shape[2] },
							     { start1, 0, 0 },
							     { count1, shape[1], shape[2] } );
	    var_v_decompressed_out =
	      writer_decompressed_io.DefineVariable<double> ("V/decompressed",
							     { shape[0], shape[1], shape[2] },
							     { start1, 0, 0 },
							     { count1, shape[1], shape[2] } );

	    writer_compressed_io.DefineAttribute<std::size_t>("shape", shape.data(), 3);
	    
	    var_u_compress_ratio =
	      writer_decompressed_io.DefineVariable<double>("U/compress_ratio", {adios2::LocalValueDim});
	    var_v_compress_ratio =
	      writer_decompressed_io.DefineVariable<double>("V/compress_ratio", {adios2::LocalValueDim});
	    var_u_compress_time =
	      writer_decompressed_io.DefineVariable<long>("U/compress_time", {adios2::LocalValueDim});
	    var_v_compress_time =
	      writer_decompressed_io.DefineVariable<long>("V/compress_time", {adios2::LocalValueDim});
	    var_u_decompress_time =
	      writer_decompressed_io.DefineVariable<long>("U/decompress_time", {adios2::LocalValueDim});
	    var_v_decompress_time =
	      writer_decompressed_io.DefineVariable<long>("V/decompress_time", {adios2::LocalValueDim});	    	    
	    
	    firstStep = false;
	  }
	
	
	writer_original.BeginStep ();
        writer_original.Put<double> (var_u_original_out, u.data());
        writer_original.Put<double> (var_v_original_out, v.data());
	writer_original.EndStep();

	size_t outSizeU = 0;
	unsigned char *bytesU = nullptr;
	size_t outSizeV = 0;
	unsigned char *bytesV = nullptr;
	double *decU = nullptr;
	double *decV = nullptr;
	void *bufferU = nullptr;
	void *bufferV = nullptr;

	long u_compress_time;
	long v_compress_time;
	long u_decompress_time;
	long v_decompress_time;
	std::chrono::steady_clock::time_point startT;
	std::chrono::steady_clock::time_point endT;	
	
	
	switch(compressor)
	  {
	  case 1:
	    startT = std::chrono::steady_clock::now();
	    bytesU = SZ_compress(SZ_DOUBLE, u.data(), &outSizeU,
				 0, 0, shape[2], shape[1], shape[0]);
	    endT = std::chrono::steady_clock::now();
	    u_compress_time = std::chrono::duration_cast<std::chrono::nanoseconds>(endT - startT).count();
	    
	    startT = std::chrono::steady_clock::now();
	    bytesV = SZ_compress(SZ_DOUBLE, v.data(), &outSizeV,
				 0, 0, shape[2], shape[1], shape[0]);
	    endT = std::chrono::steady_clock::now();
	    v_compress_time = std::chrono::duration_cast<std::chrono::nanoseconds>(endT - startT).count();
	    
	    startT = std::chrono::steady_clock::now();	    
	    decU = (double*)SZ_decompress(SZ_DOUBLE, bytesU, outSizeU,
					  0, 0, shape[2], shape[1], shape[0]);
	    endT = std::chrono::steady_clock::now();
	    u_decompress_time = std::chrono::duration_cast<std::chrono::nanoseconds>(endT - startT).count();
	    
	    startT = std::chrono::steady_clock::now();    
	    decV = (double*)SZ_decompress(SZ_DOUBLE, bytesV, outSizeV,
					  0, 0, shape[2], shape[1], shape[0]);
	    endT = std::chrono::steady_clock::now();
	    v_decompress_time = std::chrono::duration_cast<std::chrono::nanoseconds>(endT - startT).count();	    
	    break;
	  case 2:
	    ZFP_Compress_Decompress(u.data(), shape, &zfp_parameters, &zfp_output_U,
				    &u_compress_time, &u_decompress_time);
	    bytesU = (unsigned char*)zfp_output_U.compressed;
	    outSizeU = zfp_output_U.compressed_size;
	    decU = (double*)zfp_output_U.decompressed;
	    ZFP_Compress_Decompress(v.data(), shape, &zfp_parameters, &zfp_output_V,
				    &v_compress_time, &v_decompress_time);
	    bytesV = (unsigned char*)zfp_output_V.compressed;
	    decV = (double*)zfp_output_V.decompressed;
	    outSizeV = zfp_output_V.compressed_size;
	    break;
	  case 3:
	    MGARD_Compress_Decompress(u.data(), shape, &mgard_parameters, &mgard_output_U,
				      &u_compress_time, &u_decompress_time);
	    bytesU = mgard_output_U.compressed;
	    decU = mgard_output_U.decompressed;
	    outSizeU = mgard_output_U.compressed_size;
	    MGARD_Compress_Decompress(v.data(), shape, &mgard_parameters, &mgard_output_V,
				      &v_compress_time, &v_decompress_time);
	    bytesV = mgard_output_V.compressed;
	    decV = mgard_output_V.decompressed;
	    outSizeV = mgard_output_V.compressed_size;
	    break;
	  default:
	    usage();
	    MPI_Finalize();
	    return 1;	    
	  }

	double u_compress_ratio = (shape[0]*shape[1]*shape[2]*sizeof(double))/static_cast<double>(outSizeU);
	double v_compress_ratio = (shape[0]*shape[1]*shape[2]*sizeof(double))/static_cast<double>(outSizeV);

	const adios2::Dims start = {0};
	const adios2::Dims countU = {outSizeU};
	const adios2::Dims shapeU = {outSizeU};
	const adios2::Dims countV = {outSizeV};
	const adios2::Dims shapeV = {outSizeV};	
	
	writer_compressed.BeginStep ();
	var_u_compressed_out.SetShape(shapeU);
	const adios2::Box<adios2::Dims> selU(start, countU);
	var_u_compressed_out.SetSelection(selU);
	var_v_compressed_out.SetShape(shapeV);
	const adios2::Box<adios2::Dims> selV(start, countV);
	var_v_compressed_out.SetSelection(selV);	
        writer_compressed.Put<unsigned char> (var_u_compressed_out, bytesU);
        writer_compressed.Put<unsigned char> (var_v_compressed_out, bytesV);
	writer_compressed.Put<int> (var_u_size, outSizeU);
	writer_compressed.Put<int> (var_v_size, outSizeV);
	writer_compressed.EndStep();	

	writer_decompressed.BeginStep();
        writer_decompressed.Put<double> (var_u_decompressed_out, decU);
        writer_decompressed.Put<double> (var_v_decompressed_out, decV);
	writer_decompressed.Put<double> (var_u_compress_ratio, u_compress_ratio);
	writer_decompressed.Put<double> (var_v_compress_ratio, v_compress_ratio);
	writer_decompressed.Put<long> (var_u_compress_time, u_compress_time);
	writer_decompressed.Put<long> (var_v_compress_time, v_compress_time);
	writer_decompressed.Put<long> (var_u_decompress_time, u_decompress_time);
	writer_decompressed.Put<long> (var_v_decompress_time, v_decompress_time);	
	writer_decompressed.EndStep();

	switch(compressor)
	  {
	  case 1:
	    free(bytesU);
	    free(bytesV);
	    break;
	  case 2:
	    free(zfp_output_U.compressed);
	    free(zfp_output_V.compressed);
	    break;
	  case 3:
	    free(mgard_output_U.compressed);
	    free(mgard_output_V.compressed);
	    break;
	  }
	free(decU);
	free(decV);
	++stepAnalysis;
    }
  reader.Close();
  writer_original.Close();
  writer_compressed.Close();
  writer_decompressed.Close();
  MPI_Finalize();
  return 0;
}
