/*
 * Analysis code for the Gray-Scott application.
 * Reads variable U and V, compresses and decompresses them at each step, 
 * runs zchecker to compare the original and decompressed data
 * Writes zchecker statistics to separate files per variable, per step
 */

#include "zchecker.h"
#include "ftk_3D_interface.h"

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

void printUsage()
{
  std::cout<<"./compressor <input> <output> <compressor>"<<std::endl;
  std::cout<<"  compressor = 1 - SZ, 2 - ZFP, 3 - MGARD" << std::endl;
}

template<class T>
void print_step_rank(int step, int rank, std::string what, T value)
{
  std::cout << "step = " << step << " rank = " << rank << " "
	    << what << " " << value << std::endl;
}

void featurePut(std::vector<critical_point_t> & features, int offset, int total,
		adios2::Variable<double> & var_features_out, adios2::Engine & writer)
{
  int N = features.size();
  const adios2::Dims start = {static_cast<long unsigned int>(offset), 0};
  const adios2::Dims count = {static_cast<long unsigned int>(N), 4};
  const adios2::Dims shape = {static_cast<long unsigned int>(N), 4};
  var_features_out.SetShape(shape);
  const adios2::Box<adios2::Dims> sel(start, count);
  var_features_out.SetSelection(sel);
  
  adios2::Variable<double>::Span features_span =
    writer.Put<double>(var_features_out);
  for(int i = 0; i < N; ++i)
    {
      features_span.at(i+0) = features[i].x[0];
      features_span.at(i+1) = features[i].x[1];
      features_span.at(i+2) = features[i].x[2];
      features_span.at(i+3) = features[i].v;	    
    }
}

int main(int argc, char *argv[])
{
  int provided;
  MPI_Init_thread( &argc, &argv, MPI_THREAD_FUNNELED, &provided );
  int rank, comm_size, wrank;

    MPI_Comm_rank(MPI_COMM_WORLD, &wrank);

    const unsigned int color = 2;
    MPI_Comm comm;
    MPI_Comm_split(MPI_COMM_WORLD, color, wrank, &comm);

    //    MPI_Comm comm = MPI_COMM_WORLD;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &comm_size);

    if(!rank)
      std::cout<<"comm_size = " << comm_size << std::endl;
    
    char zcconfig[1024] = "zc.config";

    if (argc < 4)
    {
        std::cout << "Not enough arguments\n";
        if (rank == 0)
            printUsage();
        MPI_Finalize();
        return 0;
    }

    std::string in_filename;
    std::string out_filename;
    int compressor; // 1 - SZ, 2 - ZFP, 3 - MGARD
    
    in_filename = argv[1];
    out_filename = argv[2];
    compressor = std::stoi(argv[3]);

    std::cout << "compressor = " << compressor << std::endl;

    switch(compressor)
      {
      case 1:
	SZ_Init("sz.config");
	break;
      case 2: //todo
	break;
      case 3: //todo
	break;
      default:
	if(!rank)
	  printUsage();
	MPI_Finalize();
	return 0;
      }
    ZC_Init(zcconfig);

    
    std::size_t u_global_size, v_global_size;
    std::size_t u_local_size, v_local_size;
    
    bool firstStep = true;

    std::vector<std::size_t> shape;
    
    std::vector<double> u;
    std::vector<double> v;
    int simStep;

    adios2::Variable<double> var_u_in, var_v_in;
    adios2::Variable<int> var_step_in;
    adios2::Variable<int> var_step_out;
    adios2::Variable<double> var_u_original_out, var_v_original_out;
    adios2::Variable<double> var_u_lossy_out, var_v_lossy_out;
    adios2::Variable<double> var_u_original_features_out, var_v_original_features_out;
    adios2::Variable<double> var_u_lossy_features_out, var_v_lossy_features_out;    
    adios2::Variable<int> var_u_original_features_n_out, var_u_lossy_features_n_out,
      var_v_original_features_n_out, var_v_lossy_features_n_out;

    adios2::Variable<int> var_u_distance_d_features_out, var_v_distance_d_features_out;
    adios2::Variable<double> var_u_distance_n_features_out, var_v_distance_n_features_out;    
    
    adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);

    adios2::IO reader_io = ad.DeclareIO("SimulationOutput");
    adios2::IO writer_io = ad.DeclareIO("CompressionOutput");

    if (!rank) 
    {
        std::cout << "compression reads from Gray-Scott simulation using engine type:  "
		  << reader_io.EngineType() << std::endl;
        std::cout << "compression data is written using engine type:  "
		  << writer_io.EngineType() << std::endl;
    }

    adios2::Engine reader = reader_io.Open(in_filename,
					   adios2::Mode::Read, comm);
    adios2::Engine writer = writer_io.Open(out_filename,
					   adios2::Mode::Write, comm);

    int stepAnalysis = 0;
    while(true) {
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

        if (firstStep) {
	  var_u_original_out =
	    writer_io.DefineVariable<double> ("U/original",
					      { shape[0], shape[1], shape[2] },
					      { start1, 0, 0 },
					      { count1, shape[1], shape[2] } );
	  var_v_original_out =
	    writer_io.DefineVariable<double> ("V/original",
					      { shape[0], shape[1], shape[2] },
					      { start1, 0, 0 },
					      { count1, shape[1], shape[2] } );
	  var_u_lossy_out =
	    writer_io.DefineVariable<double> ("U/lossy",
					      { shape[0], shape[1], shape[2] },
					      { start1, 0, 0 },
					      { count1, shape[1], shape[2] } );
	  var_v_lossy_out =
	    writer_io.DefineVariable<double> ("V/lossy",
					      { shape[0], shape[1], shape[2] },
					      { start1, 0, 0 },
					      { count1, shape[1], shape[2] } );

	  var_u_original_features_out =
	    writer_io.DefineVariable<double> ("U_features/original",
					      { 1, 4},
					      { 0, 0},
					      { 1, 4} );
	  var_u_original_features_n_out =
	    writer_io.DefineVariable<int>("U_features_n/original", {adios2::LocalValueDim});
	  var_v_original_features_out =
	    writer_io.DefineVariable<double> ("V_features/original",
					      { 1, 4},
					      { 0, 0},
					      { 1, 4} );
	  var_v_original_features_n_out =
	    writer_io.DefineVariable<int>("V_features_n/original", {adios2::LocalValueDim});	  
	  var_u_lossy_features_out =
	    writer_io.DefineVariable<double> ("U_features/lossy",
					      { 1, 4},
					      { 0, 0},
					      { 1, 4} );
	  var_u_lossy_features_n_out =
	    writer_io.DefineVariable<int>("U_features_n/lossy", {adios2::LocalValueDim});	  
	  var_v_lossy_features_out =
	    writer_io.DefineVariable<double> ("V_features/lossy",
					      { 1, 4},
					      { 0, 0},
					      { 1, 4} );
	  var_v_lossy_features_n_out =
	    writer_io.DefineVariable<int>("V_features_n/lossy", {adios2::LocalValueDim});
	    
	  var_u_distance_d_features_out =
	    writer_io.DefineVariable<int>("U_features_distance/difference", {adios2::LocalValueDim});
	  var_u_distance_n_features_out =
	    writer_io.DefineVariable<double>("U_features_distance/normalized", {adios2::LocalValueDim});
	  var_v_distance_d_features_out =
	    writer_io.DefineVariable<int>("V_features_distance/difference", {adios2::LocalValueDim});
	  var_v_distance_n_features_out =
	    writer_io.DefineVariable<double>("V_features_distance/normalized", {adios2::LocalValueDim});	    
	  firstStep = false;
        }

        reader.Get<double>(var_u_in, u);
        reader.Get<double>(var_v_in, v);
        reader.EndStep();
	
	std::vector<critical_point_t> features_original_u =
	  extract_features(u.data(), local_shape[0], local_shape[1], local_shape[2]);
	std::vector<critical_point_t> features_original_v =
	  extract_features(v.data(), local_shape[0], local_shape[1], local_shape[2]);	

	print_step_rank(stepAnalysis, rank, "features_original_u", features_original_u.size());
	print_step_rank(stepAnalysis, rank, "features_original_v", features_original_v.size());	
	
	double *lossy_u = nullptr;
	double *lossy_v = nullptr;

	switch(compressor)
	  {
	  case 1:
	    lossy_u = z_check_sz(stepAnalysis, u, std::string("u_sz"), local_shape);
	    lossy_v = z_check_sz(stepAnalysis, v, std::string("v_sz"), local_shape);	
	    break;
	  case 2:
	    lossy_u = z_check_zfp(stepAnalysis, u, std::string("u_zfp"));
	    lossy_v = z_check_zfp(stepAnalysis, v, std::string("v_zfp"));
	    break;
	  case 3:
	    lossy_u = z_check_mgard(stepAnalysis, u, std::string("u_mgard"), local_shape);
	    lossy_v = z_check_mgard(stepAnalysis, v, std::string("v_mgard"), local_shape);
	    break;
	  default:
	    if(!rank)
	      printUsage();
	    MPI_Finalize();
	    return 0;
	  }

	std::vector<critical_point_t> features_lossy_u =
	  extract_features(lossy_u, local_shape[0], local_shape[1], local_shape[2]);
	std::vector<critical_point_t> features_lossy_v =
	  extract_features(lossy_v, local_shape[0], local_shape[1], local_shape[2]);	


	print_step_rank(stepAnalysis, rank, "features_lossy_u", features_lossy_u.size());
	print_step_rank(stepAnalysis, rank, "features_lossy_v", features_lossy_v.size());	

	int distance_u_diff, distance_v_diff;
	double distance_u_norm, distance_v_norm;	
	
	distance_between_features(features_original_u, features_lossy_u,
				  &distance_u_diff, &distance_u_norm);
	distance_between_features(features_original_v, features_lossy_v,
				  &distance_v_diff, &distance_v_norm);

	print_step_rank(stepAnalysis, rank, "distance_u_diff", distance_u_diff);
	print_step_rank(stepAnalysis, rank, "distance_v_diff", distance_v_diff);
	print_step_rank(stepAnalysis, rank, "distance_u_norm", distance_u_norm);
	print_step_rank(stepAnalysis, rank, "distance_v_diff", distance_v_norm);		

	int nuo = features_original_u.size();
	int nul = features_lossy_u.size();
	int nvo = features_original_v.size();
	int nvl = features_lossy_v.size();

	int *nuo_a = new int[comm_size];
	int *nul_a = new int[comm_size];
	int *nvo_a = new int[comm_size];
	int *nvl_a = new int[comm_size];	

	MPI_Allgather(&nuo, 1, MPI_INT, nuo_a, comm_size, MPI_INT, comm);
	MPI_Allgather(&nul, 1, MPI_INT, nul_a, comm_size, MPI_INT, comm);
	MPI_Allgather(&nvo, 1, MPI_INT, nvo_a, comm_size, MPI_INT, comm);
	MPI_Allgather(&nvl, 1, MPI_INT, nvl_a, comm_size, MPI_INT, comm);	

	int nuo_n, nuo_offset;
	nuo_offset = scan(nuo_a, rank, comm_size, &nuo_n);
	int nul_n, nul_offset;
	nul_offset = scan(nul_a, rank, comm_size, &nul_n);
	int nvo_n, nvo_offset;
	nvo_offset = scan(nvo_a, rank, comm_size, &nvo_n);
	int nvl_n, nvl_offset;
	nvl_offset = scan(nvl_a, rank, comm_size, &nvl_n);	

    
        writer.BeginStep ();
        writer.Put<double> (var_u_original_out, u.data());
        writer.Put<double> (var_v_original_out, v.data());
        writer.Put<double> (var_u_lossy_out, lossy_u);
        writer.Put<double> (var_v_lossy_out, lossy_v);
	
	featurePut(features_original_u, nuo_offset, nuo_n,
		   var_u_original_features_out, writer);
	featurePut(features_original_v, nvo_offset, nvo_n,
		   var_v_original_features_out, writer);
	featurePut(features_lossy_u, nul_offset, nul_n,
		   var_u_lossy_features_out, writer);
	featurePut(features_lossy_v, nvl_offset, nvl_n,
		   var_v_lossy_features_out, writer);
	
        writer.EndStep ();
	
        if (!rank)
        {
	  std::cout << "compression step " << stepAnalysis
		    << " processing sim output step "
		    << stepSimOut << std::endl;
        }
	free(lossy_u);
	free(lossy_v);
        ++stepAnalysis;
    }

    reader.Close();
    if(!rank)
      std::cout << "After closing reader" << std::endl;
    writer.Close();
    if(!rank)
      std::cout << "After closing writer" << std::endl;    
    if(compressor == 1)
      SZ_Finalize();
    if(!rank)
      std::cout << "After SZ_Finalize" << std::endl;    
    ZC_Finalize();
    if(!rank)
      std::cout << "After ZC_Finalize" << std::endl;        
    MPI_Finalize();

    return 0;
}

