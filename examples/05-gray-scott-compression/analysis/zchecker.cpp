#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include <mpi.h>
#include <adios2.h>
#include <zc.h>


void usage()
{
  std::cout << "mpirun -n <N> zchecker <original data file> <lossy data file>" << std::endl;
}

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  int rank, comm_size, wrank;

  MPI_Comm_rank(MPI_COMM_WORLD, &wrank);
  const unsigned int color = 2;
  MPI_Comm comm;
  MPI_Comm_split(MPI_COMM_WORLD, color, wrank, &comm);

  MPI_Comm_rank(comm, &rank);
  MPI_Comm_size(comm, &comm_size);

  if(argc != 3)
    {
      if(!rank)
	usage();
      MPI_Finalize();
      return 1;

    }

  std::string original_fn = argv[1];
  std::string lossy_fn = argv[2];
  char  zcconfig[] = "zc.config";
  
  ZC_Init(zcconfig);

  std::size_t u_global_size, v_global_size;
  std::size_t u_local_size, v_local_size;  
  //bool firstStep = true;
  std::vector<std::size_t> shape;
    
  std::vector<double> u_original;
  std::vector<double> v_original;
  std::vector<double> u_lossy;
  std::vector<double> v_lossy;
  
  //int simStep_original;

  adios2::Variable<double> var_u_original, var_v_original;
  adios2::Variable<int> var_step_original;
  adios2::Variable<double> var_u_lossy, var_v_lossy;
  adios2::Variable<int> var_step_lossy;  
 
  adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);
  adios2::IO reader_original_io = ad.DeclareIO("Original");
  adios2::IO reader_lossy_io = ad.DeclareIO("Lossy");  

  adios2::Engine reader_original = reader_original_io.Open(original_fn,
						  adios2::Mode::Read, comm);
  adios2::Engine reader_lossy = reader_lossy_io.Open(lossy_fn,
					       adios2::Mode::Read, comm);

  int stepAnalysis = 0;
  while(true)
    {
      adios2::StepStatus read_original_status = reader_original.BeginStep();
      if (read_original_status == adios2::StepStatus::NotReady)
	{
	  std::this_thread::sleep_for(std::chrono::milliseconds(1000));
	  continue;
	}
      else if (read_original_status != adios2::StepStatus::OK)
	{
	  break;
	}
      
      int step_original = reader_original.CurrentStep();
      var_u_original = reader_original_io.InquireVariable<double>("U/original");
      var_v_original = reader_original_io.InquireVariable<double>("V/original");
      var_step_original = reader_original_io.InquireVariable<int>("step");
      shape = var_u_original.Shape();
      
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
      
      var_u_original.SetSelection(adios2::Box<adios2::Dims>(
							    {start1, 0, 0},
							    {count1, shape[1], shape[2]}));
      var_v_original.SetSelection(adios2::Box<adios2::Dims>(
							    {start1, 0, 0},
							    {count1, shape[1], shape[2]}));
      
      reader_original.Get<double>(var_u_original, u_original);
      reader_original.Get<double>(var_v_original, v_original);
      reader_original.EndStep();

      adios2::StepStatus read_lossy_status = reader_lossy.BeginStep();
      if (read_lossy_status == adios2::StepStatus::NotReady)
	{
	  std::this_thread::sleep_for(std::chrono::milliseconds(1000));
	  continue;
	}
      else if (read_lossy_status != adios2::StepStatus::OK)
	{
	  break;
	}
      
      int step_lossy = reader_lossy.CurrentStep();
      var_u_lossy = reader_lossy_io.InquireVariable<double>("U/decompressed");
      var_v_lossy = reader_lossy_io.InquireVariable<double>("V/decompressed");
      var_step_lossy = reader_lossy_io.InquireVariable<int>("step");

      var_u_lossy.SetSelection(adios2::Box<adios2::Dims>(
							 {start1, 0, 0},
							 {count1, shape[1], shape[2]}));
      var_v_lossy.SetSelection(adios2::Box<adios2::Dims>(
							 {start1, 0, 0},
							 {count1, shape[1], shape[2]}));
      
      reader_lossy.Get<double>(var_u_lossy, u_lossy);
      reader_lossy.Get<double>(var_v_lossy, v_lossy);
      reader_lossy.EndStep();

      char varNameU[] = "U";
      char varNameV[] = "V";
      ZC_CompareData * compareU =  ZC_compareData(varNameU, ZC_DOUBLE , u_original.data(),
						  u_lossy.data(), 0, 0, shape[0], shape[1], shape[2]);
      //ZC_printCompressionResult(compareU);
      ZC_CompareData * compareV =  ZC_compareData(varNameV, ZC_DOUBLE , v_original.data(),
						  v_lossy.data(), 0, 0, shape[0], shape[1], shape[2]);
      //ZC_printCompressionResult(compareV);
      //ZC_writeCompressionResult(ZC_CompareData* compareResult, char* solution, char* varName, char* tgtWorkspaceDir);
      char dirU[]="outputU";
      char dirV[]="outputV";
      char solutionU[16];
      sprintf(solutionU, "%d", stepAnalysis);
      char solutionV[16];
      sprintf(solutionV, "%d", stepAnalysis);      
      ZC_writeCompressionResult(compareU, solutionU, varNameU, dirU);
      ZC_writeCompressionResult(compareV, solutionV, varNameV, dirV);      

      freeCompareResult(compareU);
      freeCompareResult(compareV);      
      ++stepAnalysis;	      
    }
  
  reader_original.Close();
  reader_lossy.Close();
  ZC_Finalize();
  MPI_Finalize();
  return 0;
}
