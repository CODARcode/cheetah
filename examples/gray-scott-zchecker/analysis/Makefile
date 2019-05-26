zchecker: zchecker.cpp
	mpicxx zchecker.cpp `adios2-config --cxx-flags --cxx-libs` -I${SZ_DIR}/include -L${SZ_DIR}/lib -lSZ -I${Z_CHECKER_DIR}/include -L${Z_CHECKER_DIR}/lib -lzc -I{ZFP_DIR}/include -L${ZFP_DIR}/lib -lzfp -I${MGARD_DIR}/include -L${MGARD_DIR}/lib -lmgard -o zchecker
clean:
	rm -f a.out zchecker *~ *.o

