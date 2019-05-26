/*
 * Analysis code for the Gray-Scott application.
 * Reads variable U and V, compresses and decompresses them at each step, runs zchecker to compare
 * original and decompressed data
 * Writes zchecker statistics to file
 */

#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <cstdint>
#include <cmath>
#include <chrono>
#include <string>
#include <thread>
#include "sz.h"
#include "adios2.h"
#include "zc.h"
#include "zfp.h"
extern "C" {
#include "mgard_capi.h"
}
  
void printUsage()
{
  std::cout<<"Hello"<<std::endl;
}

void z_check_mgard(int stepAnalysis, std::vector<double>& u, const std::string &solution)
{
  std::string tstr = std::to_string(stepAnalysis);
  char varName[1024];
  strcpy(varName, tstr.c_str());
  ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(), 0, 0, 0, 0, u.size());
  double * tmp = (double*)malloc(u.size()*sizeof(double));
  for(int i = 0; i < u.size(); ++i) tmp[i] = u[i];
  double tolerance = 1.e-8;
  int outSize;
  int nfib=15;
  unsigned char *bytes = mgard_compress(1, tmp, &outSize, 1, u.size(), nfib, &tolerance);
  std::cout << "inSize  = " << u.size()*sizeof(double) << std::endl; 
  std::cout << "outSize = " << outSize << std::endl;
  std::cout.flush();
  
  char s[1024];
  strcpy(s, solution.c_str());
  ZC_CompareData* compareResult = ZC_endCmpr(dataProperty, s, outSize);

  ZC_startDec();

  double * decData = (double*)mgard_decompress(1, bytes, outSize, 1, u.size(), nfib);
  ZC_endDec(compareResult, decData);
  ZC_printCompressionResult(compareResult);

  freeDataProperty(dataProperty);
  freeCompareResult(compareResult);
  free(bytes);
  free(decData);  
}


void z_check_zfp(int stepAnalysis, std::vector<double>& u, const std::string &solution)
{
  std::string tstr = std::to_string(stepAnalysis);
  char varName[1024];
  strcpy(varName, tstr.c_str());
  ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(), 0, 0, 0, 0, u.size());

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
  void* decData = malloc(u.size()*sizeof(double));
  zfp_field* field_dec = zfp_field_1d(decData, type, u.size());
  zfp_stream_rewind(zfp);
  size_t size = zfp_decompress(zfp, field_dec);

  ZC_endDec(compareResult, decData);
  ZC_printCompressionResult(compareResult);

  freeDataProperty(dataProperty);
  freeCompareResult(compareResult);
  free(buffer);
  free(decData);
}

void z_check_sz(int stepAnalysis, std::vector<double>& u, const std::string &solution)
{
	std::string tstr = std::to_string(stepAnalysis);
	char varName[1024];
	strcpy(varName, tstr.c_str());
	ZC_DataProperty* dataProperty = ZC_startCmpr(varName, ZC_DOUBLE, u.data(), 0, 0, 0, 0, u.size());	
	size_t outSize;

	unsigned char *bytes = SZ_compress(SZ_DOUBLE, u.data(), &outSize, 0, 0, 0, 0, u.size());
	std::cout << "outSize=" << outSize << std::endl;
	std::cout.flush();
	
	char s[1024];
	strcpy(s, solution.c_str());
	ZC_CompareData* compareResult = ZC_endCmpr(dataProperty, s, outSize);

	ZC_startDec();
	double *decData = (double*)SZ_decompress(SZ_DOUBLE, bytes, outSize, 0, 0, 0, 0, u.size());

	ZC_endDec(compareResult, decData);
	ZC_printCompressionResult(compareResult);

	freeDataProperty(dataProperty);
	freeCompareResult(compareResult);
	free(bytes);
	free(decData);	
}



int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);
    int rank, comm_size, wrank;

    MPI_Comm_rank(MPI_COMM_WORLD, &wrank);

    const unsigned int color = 2;
    MPI_Comm comm;
    MPI_Comm_split(MPI_COMM_WORLD, color, wrank, &comm);

    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &comm_size);

    char szconfig[1024] = "sz.config";
    char zcconfig[1024] = "zc.config";
    SZ_Init(szconfig);
    ZC_Init(zcconfig);

    if (argc < 3)
    {
        std::cout << "Not enough arguments\n";
        if (rank == 0)
            printUsage();
        MPI_Finalize();
        return 0;
    }

    std::string in_filename;
    std::string out_filename;

    //    bool write_inputvars = false;
    in_filename = argv[1];
    out_filename = argv[2];

    std::size_t u_global_size, v_global_size;
    std::size_t u_local_size, v_local_size;
    
    bool firstStep = true;

    std::vector<std::size_t> shape;
    
    std::vector<double> u;
    std::vector<double> v;
    int simStep;

    // adios2 variable declarations
    adios2::Variable<double> var_u_in, var_v_in;
    adios2::Variable<int> var_step_in;
    adios2::Variable<int> var_step_out;
    adios2::Variable<double> var_u_out, var_v_out;

    // adios2 io object and engine init
    adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);

    // IO objects for reading and writing
    adios2::IO reader_io = ad.DeclareIO("SimulationOutput");
    // adios2::IO writer_io = ad.DeclareIO("PDFAnalysisOutput");
    if (!rank) 
    {
        std::cout << "zchecker reads from Gray-Scott simulation using engine type:  " << reader_io.EngineType() << std::endl;
        //std::cout << "PDF analysis writes using engine type:                 " << writer_io.EngineType() << std::endl;
    }

    // Engines for reading and writing
    adios2::Engine reader = reader_io.Open(in_filename, adios2::Mode::Read, comm);

    int stepAnalysis = 0;
    while(true) {

        // Begin step
        adios2::StepStatus read_status = reader.BeginStep(adios2::StepMode::NextAvailable, 10.0f);
        if (read_status == adios2::StepStatus::NotReady)
        {
            // std::cout << "Stream not ready yet. Waiting...\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            continue;
        }
        else if (read_status != adios2::StepStatus::OK)
        {
            break;
        }
 
        int stepSimOut = reader.CurrentStep();

        // Inquire variable and set the selection at the first step only
        // This assumes that the variable dimensions do not change across timesteps

        // Inquire variable
        var_u_in = reader_io.InquireVariable<double>("U");
        var_v_in = reader_io.InquireVariable<double>("V");
        var_step_in = reader_io.InquireVariable<int>("step");
        shape = var_u_in.Shape();

        // Calculate global and local sizes of U and V
        u_global_size = shape[0] * shape[1] * shape[2];
        u_local_size  = u_global_size/comm_size;
        v_global_size = shape[0] * shape[1] * shape[2];
        v_local_size  = v_global_size/comm_size;

        size_t count1 = shape[0]/comm_size;
        size_t start1 = count1 * rank;
        if (rank == comm_size-1) {
            // last process need to read all the rest of slices
            count1 = shape[0] - count1 * (comm_size - 1);
        }

        /*std::cout << "  rank " << rank << " slice start={" <<  start1 
            << ",0,0} count={" << count1  << "," << shape[1] << "," << shape[2]
            << "}" << std::endl;*/

        // Set selection
        var_u_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1,0,0},
                    {count1, shape[1], shape[2]}));
        var_v_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1,0,0},
                    {count1, shape[1], shape[2]}));

        // Read adios2 data
        reader.Get<double>(var_u_in, u);
        reader.Get<double>(var_v_in, v);

        // End adios2 step
        reader.EndStep();
	/*
	z_check_sz(stepAnalysis, u, std::string("u_sz"));
	z_check_sz(stepAnalysis, v, std::string("v_sz"));	

	z_check_zfp(stepAnalysis, u, std::string("u_zfp"));
	z_check_zfp(stepAnalysis, v, std::string("v_zfp"));
	*/
	
	z_check_mgard(stepAnalysis, u, std::string("u_mgard"));
	z_check_mgard(stepAnalysis, v, std::string("v_mgard"));			
	
        if (!rank)
        {
            std::cout << "PDF Analysis step " << stepAnalysis
                << " processing sim output step "
                << stepSimOut << " sim compute step " << simStep << std::endl;
        }
	
        ++stepAnalysis;
    }

    // cleanup
    reader.Close();
    SZ_Finalize();
    ZC_Finalize();
    MPI_Finalize();
    return 0;
}

