#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <omp.h>

int main(int argc, char** argv) {
    int rank, size;
    MPI_Init(&argc, &argv);

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
#pragma omp parallel
    printf("%s Rank %d of %d, Thread %d of %d\n", argv[0], rank+1, size, omp_get_thread_num()+1, omp_get_num_threads());

    MPI_Finalize();
    return 0;
}

