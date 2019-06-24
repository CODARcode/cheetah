/*
 * Analysis code for the Gray-Scott application.
 * Reads variable U and V, compresses and decompresses them at each step, 
 * runs zchecker to compare the original and decompressed data
 * Writes zchecker statistics to separate files per variable, per step
 */

#include "zchecker.h"
#include "ftk_3D_interface.h"

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
    //std::string out_filename;

    //    bool write_inputvars = false;
    in_filename = argv[1];
    //out_filename = argv[2];

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
    adios2::Variable<double> var_u_original_out, var_v_original_out;
    adios2::Variable<double> var_u_lossy_out, var_v_lossy_out;
    
    adios2::Variable<double> var_u_original_features_out, var_v_original_features_out;
    adios2::Variable<double> var_u_lossy_features_out, var_v_lossy_features_out;    

    // adios2 io object and engine init
    adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);

    // IO objects for reading and writing
    adios2::IO reader_io = ad.DeclareIO("SimulationOutput");
    adios2::IO writer_io = ad.DeclareIO("CompressionOutput");
    if (!rank) 
    {
        std::cout << "zchecker reads from Gray-Scott simulation using engine type:  "
		  << reader_io.EngineType() << std::endl;
        std::cout << "Compression data is written using engine type:  "
		  << writer_io.EngineType() << std::endl;
    }

    // Engines for reading and writing
    adios2::Engine reader = reader_io.Open(in_filename,
					   adios2::Mode::Read, comm);
    adios2::Engine writer = writer_io.Open("CompressionOutput",
					   adios2::Mode::Write, comm);

    int stepAnalysis = 0;
    while(true) {

        // Begin step
        adios2::StepStatus read_status = reader.BeginStep(adios2::StepMode::NextAvailable,
							  10.0f);
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
	    writer_io.DefineVariable<double> ("U/features/original",
					      { 1, 4},
					      { 0, 0},
					      { 1, 4} );

	  
	  firstStep = false;
        }


	
        // Read adios2 data
        reader.Get<double>(var_u_in, u);
        reader.Get<double>(var_v_in, v);

        // End adios2 step
        reader.EndStep();
	
	std::vector<critical_point_t> features_original_u =
	  extract_features(u.data(), shape[2], shape[1], shape[0]);
	std::vector<critical_point_t> features_original_v =
	  extract_features(v.data(), shape[2], shape[1], shape[0]);	

	std::cout<<"step = " << stepAnalysis << " features_original_u " << features_original_u.size() << std::endl;
	std::cout<<"step = " << stepAnalysis << " features_original_v " << features_original_v.size() << std::endl;	
	
	
	auto lossy_u = z_check_sz(stepAnalysis, u, std::string("u_sz"), shape);
	auto lossy_v = z_check_sz(stepAnalysis, v, std::string("v_sz"), shape);	

	std::vector<critical_point_t> features_lossy_sz_u =
	  extract_features(lossy_u, shape[2], shape[1], shape[0]);
	std::vector<critical_point_t> features_lossy_sz_v =
	  extract_features(lossy_v, shape[2], shape[1], shape[0]);	


	std::cout<<"step = " << stepAnalysis << " features_lossy_sz_u " << features_lossy_sz_u.size() << std::endl;
	std::cout<<"step = " << stepAnalysis << " features_lossy_sz_v " << features_lossy_sz_v.size() << std::endl;	

	
	double distance_sz_u = distance_between_features(features_original_u, features_lossy_sz_u);
	double distance_sz_v = distance_between_features(features_original_v, features_lossy_sz_v);	
	//	std::cout << "distance_sz_u = " << distance_sz_u << std::endl;
	//	std::cout << "distance_sz_v = " << distance_sz_v << std::endl;	

	
	z_check_zfp(stepAnalysis, u, std::string("u_zfp"));
	z_check_zfp(stepAnalysis, v, std::string("v_zfp"));

	z_check_mgard(stepAnalysis, u, std::string("u_mgard"), shape);
	z_check_mgard(stepAnalysis, v, std::string("v_mgard"), shape);


        writer.BeginStep ();
        writer.Put<double> (var_u_original_out, u.data());
        writer.Put<double> (var_v_original_out, v.data());

	// to change later
        writer.Put<double> (var_u_lossy_out, lossy_u);
        writer.Put<double> (var_v_lossy_out, lossy_v);

	int Ny = features_original_u.size()/comm_size;
	const adios2::Dims start = {rank*Ny, 0};
	if(rank == comm_size - 1)
	  Ny = features_original_u.size() - Ny*rank;
	if(Ny > 0)
	  {
	    const adios2::Dims count = {Ny, 4};
	    const adios2::Box<adios2::Dims> sel(start, count);
	    var_u_original_features_out.SetSelection(sel);
	
	    const adios2::Dims shape = {features_original_u.size(), 4};
	    var_u_original_features_out.SetShape(shape);

	    adios2::Variable<double>::Span features_original_u_span = writer.Put<double>(var_u_original_features_out);
	    for(int i = 0; i < features_original_u.size(); ++i)
	      {
		features_original_u_span.at(i+0) = features_original_u[i].x[0];
		features_original_u_span.at(i+1) = features_original_u[i].x[1];
		features_original_u_span.at(i+2) = features_original_u[i].x[2];
		features_original_u_span.at(i+3) = features_original_u[i].v;	    
	      }
	  }
	    
        writer.EndStep ();
	
	
        if (!rank)
        {
            std::cout << "Z-Checker Analysis step " << stepAnalysis
                << " processing sim output step "
                << stepSimOut << " sim compute step " << simStep << std::endl;
        }
	free(lossy_u);
	free(lossy_v);
        ++stepAnalysis;
    }

    // cleanup
    reader.Close();
    writer.Close();
    SZ_Finalize();
    ZC_Finalize();
    MPI_Finalize();

    return 0;
}

