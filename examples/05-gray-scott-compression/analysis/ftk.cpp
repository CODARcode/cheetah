#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include <mpi.h>
#include <adios2.h>
#include "ftk_3D_interface.h"

void usage()
{
  std::cout << "mpirun -n 1 ftk_main <original data file> <lossy data file> <output file> <nthreads>" << std::endl;
}

int scan(int *sizes, int rank, int n, int *total)
{
  int subtotal = 0;
  for(int i=0;i<rank;++i)
      subtotal += sizes[i];
  *total = subtotal;
  for(int i = rank; i < n; ++i)
    *total += sizes[i];
  return subtotal;
}

void featurePut(std::vector<critical_point_t> & features, int offset, int total,
                adios2::Variable<double> & var_features_out, adios2::Engine & writer)
{
  int N = features.size();
  //  std::cout<<"In featurePut N = " << N << " total = " << total << " offset=" << offset << std::endl;
  const adios2::Dims start = {static_cast<long unsigned int>(offset), 0};
  const adios2::Dims count = {static_cast<long unsigned int>(N), 4};
  const adios2::Dims shape = {static_cast<long unsigned int>(total), 4};
  var_features_out.SetShape(shape);
  const adios2::Box<adios2::Dims> sel(start, count);
  var_features_out.SetSelection(sel);
  
  adios2::Variable<double>::Span features_span =
    writer.Put<double>(var_features_out);
  
  for(int i = 0, j = 0; i < N; ++i, j+=4)
    {
      features_span.at(j+0) = features[i].x[0];
      features_span.at(j+1) = features[i].x[1];
      features_span.at(j+2) = features[i].x[2];
      features_span.at(j+3) = features[i].v;        
    }
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
      std::cout << "Currently only 1 MPI rank is supported" << std::endl;
      usage();
      MPI_Finalize();
      return 1;
    }
  
  if(argc != 5)
    {
      if(!rank)
	usage();
      MPI_Finalize();
      return 1;

    }

  std::string original_fn = argv[1];
  std::string lossy_fn = argv[2];
  std::string ftk_fn = argv[3];
  int nthreads = std::stoi(argv[4]);
  
  std::size_t u_global_size, v_global_size;
  std::size_t u_local_size, v_local_size;  
  std::vector<std::size_t> shape;
  bool firstStep = true;
    
  std::vector<double> u_original;
  std::vector<double> v_original;
  std::vector<double> u_lossy;
  std::vector<double> v_lossy;

  adios2::Variable<double> var_u_original, var_v_original;
  adios2::Variable<int> var_step_original;
  adios2::Variable<double> var_u_lossy, var_v_lossy;
  adios2::Variable<int> var_step_lossy;  

  adios2::Variable<double> var_u_original_out, var_v_original_out;
  adios2::Variable<double> var_u_lossy_out, var_v_lossy_out;
  adios2::Variable<double> var_u_original_features_out, var_v_original_features_out;
  adios2::Variable<double> var_u_lossy_features_out, var_v_lossy_features_out;    
  adios2::Variable<int> var_u_original_features_n_out, var_u_lossy_features_n_out,
    var_v_original_features_n_out, var_v_lossy_features_n_out;
  
  adios2::Variable<int> var_u_distance_d_features_out, var_v_distance_d_features_out;
  adios2::Variable<double> var_u_distance_n_features_out, var_v_distance_n_features_out;    
  
  adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);
  adios2::IO reader_original_io = ad.DeclareIO("OriginalOutput");
  adios2::IO reader_lossy_io = ad.DeclareIO("DecompressedOutput");
  adios2::IO writer_ftk_io = ad.DeclareIO("FTK");

  adios2::Engine reader_original = reader_original_io.Open(original_fn,
						  adios2::Mode::Read, comm);
  adios2::Engine reader_lossy = reader_lossy_io.Open(lossy_fn,
					       adios2::Mode::Read, comm);
  adios2::Engine writer_ftk = writer_ftk_io.Open(ftk_fn,
					 adios2::Mode::Write, comm);

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
      if (firstStep)
	{
          var_u_original_features_out =
            writer_ftk_io.DefineVariable<double> ("U_features/original",
                                              { 1, 4},
                                              { 0, 0},
                                              { 1, 4} );
          var_u_original_features_n_out =
            writer_ftk_io.DefineVariable<int>("U_features_n/original", {adios2::LocalValueDim});
          var_v_original_features_out =
            writer_ftk_io.DefineVariable<double> ("V_features/original",
                                              { 1, 4},
                                              { 0, 0},
                                              { 1, 4} );
          var_v_original_features_n_out =
            writer_ftk_io.DefineVariable<int>("V_features_n/original", {adios2::LocalValueDim});      
          var_u_lossy_features_out =
            writer_ftk_io.DefineVariable<double> ("U_features/lossy",
                                              { 1, 4},
                                              { 0, 0},
                                              { 1, 4} );
          var_u_lossy_features_n_out =
            writer_ftk_io.DefineVariable<int>("U_features_n/lossy", {adios2::LocalValueDim});         
          var_v_lossy_features_out =
            writer_ftk_io.DefineVariable<double> ("V_features/lossy",
                                              { 1, 4},
                                              { 0, 0},
                                              { 1, 4} );
          var_v_lossy_features_n_out =
            writer_ftk_io.DefineVariable<int>("V_features_n/lossy", {adios2::LocalValueDim});
	  
          var_u_distance_d_features_out =
            writer_ftk_io.DefineVariable<int>("U_features_distance/difference", {adios2::LocalValueDim});
          var_u_distance_n_features_out =
            writer_ftk_io.DefineVariable<double>("U_features_distance/normalized", {adios2::LocalValueDim});
          var_v_distance_d_features_out =
            writer_ftk_io.DefineVariable<int>("V_features_distance/difference", {adios2::LocalValueDim});
          var_v_distance_n_features_out =
            writer_ftk_io.DefineVariable<double>("V_features_distance/normalized", {adios2::LocalValueDim});            
          firstStep = false;
	}
      
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

      //FTK start

      std::vector<critical_point_t> features_original_u =
	extract_features(u_original.data(), local_shape[0], local_shape[1], local_shape[2], nthreads);
      std::vector<critical_point_t> features_original_v =
	extract_features(v_original.data(), local_shape[0], local_shape[1], local_shape[2], nthreads);

      std::vector<critical_point_t> features_lossy_u =
	extract_features(u_lossy.data(), local_shape[0], local_shape[1], local_shape[2], nthreads);
      std::vector<critical_point_t> features_lossy_v =
	extract_features(v_lossy.data(), local_shape[0], local_shape[1], local_shape[2], nthreads);

      int distance_u_diff, distance_v_diff;
      double distance_u_norm, distance_v_norm;
      
      distance_between_features(features_original_u, features_lossy_u,
				&distance_u_diff, &distance_u_norm);
      distance_between_features(features_original_v, features_lossy_v,
				&distance_v_diff, &distance_v_norm);

      const int nuo = features_original_u.size();
      const int nul = features_lossy_u.size();
      const int nvo = features_original_v.size();
      const int nvl = features_lossy_v.size();
      
      int *nuo_a = new int[comm_size];
      int *nul_a = new int[comm_size];
      int *nvo_a = new int[comm_size];
      int *nvl_a = new int[comm_size];

      MPI_Allgather(&nuo, 1, MPI_INT, nuo_a, 1, MPI_INT, comm);
      MPI_Allgather(&nul, 1, MPI_INT, nul_a, 1, MPI_INT, comm);
      MPI_Allgather(&nvo, 1, MPI_INT, nvo_a, 1, MPI_INT, comm);
      MPI_Allgather(&nvl, 1, MPI_INT, nvl_a, 1, MPI_INT, comm);

      int nuo_n, nuo_offset;
      nuo_offset = scan(nuo_a, rank, comm_size, &nuo_n);
      int nul_n, nul_offset;
      nul_offset = scan(nul_a, rank, comm_size, &nul_n);
      int nvo_n, nvo_offset;
      nvo_offset = scan(nvo_a, rank, comm_size, &nvo_n);
      int nvl_n, nvl_offset;
      nvl_offset = scan(nvl_a, rank, comm_size, &nvl_n);

      writer_ftk.BeginStep ();
      writer_ftk.Put<int>(var_u_original_features_n_out, &nuo);
      writer_ftk.Put<int>(var_v_original_features_n_out, &nvo);
      writer_ftk.Put<int>(var_u_lossy_features_n_out, &nul);
      writer_ftk.Put<int>(var_v_lossy_features_n_out, &nvl);
      
      writer_ftk.Put<int>(var_u_distance_d_features_out, distance_u_diff);
      writer_ftk.Put<int>(var_v_distance_d_features_out, distance_v_diff);
      writer_ftk.Put<double>(var_u_distance_n_features_out, distance_u_norm);
      writer_ftk.Put<double>(var_v_distance_n_features_out, distance_v_norm);
      
      featurePut(features_original_u, nuo_offset, nuo_n,
		 var_u_original_features_out, writer_ftk);
      featurePut(features_original_v, nvo_offset, nvo_n,
		 var_v_original_features_out, writer_ftk);
      featurePut(features_lossy_u, nul_offset, nul_n,
		 var_u_lossy_features_out, writer_ftk);
      featurePut(features_lossy_v, nvl_offset, nvl_n,
		 var_v_lossy_features_out, writer_ftk);
      
      writer_ftk.EndStep ();
      
      //FTK end     
      ++stepAnalysis;	      
    }
  
  reader_original.Close();
  reader_lossy.Close();
  writer_ftk.Close();
  MPI_Finalize();
  return 0;
}
