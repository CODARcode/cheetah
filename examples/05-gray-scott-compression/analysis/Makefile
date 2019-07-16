DEPS=sz_local.h mgard_local.h zfp_local.h
DEBUG=-g
CXXFLAGS=`adios2-config --cxx-flags` -I${SZ_DIR}/include -I${ZFP_DIR}/include -I${MGARD_DIR}/include -I${Z_CHECKER_DIR}/include -std=c++1z ${DEBUG}
LIBS=`adios2-config --cxx-libs` -L${SZ_DIR}/lib -lSZ -lzstd -lzlib -L${ZFP_DIR}/lib -lzfp -L${MGARD_DIR}/lib -lmgard -L${Z_CHECKER_DIR}/lib -lzc  ${DEBUG}
CXX=mpicxx

compress: compress.o sz_local.o zfp_local.o mgard_local.o
	$(CXX) compress.o sz_local.o zfp_local.o mgard_local.o $(LIBS) -o compress

zchecker: zchecker.o
	$(CXX) zchecker.o $(LIBS) -o zchecker

%.o: %.cpp $(DEPS)
	$(CXX) -c -o $@ $< $(CXXFLAGS)

clean:
	rm -rf outputU outputV compress zchecker *~ *.o *.ps

