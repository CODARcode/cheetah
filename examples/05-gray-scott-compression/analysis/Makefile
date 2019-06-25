DEPS=zchecker.h ftk_3D_interface.h
DEBUG=-g
CXXFLAGS=`adios2-config --cxx-flags` -I${SZ_DIR}/include -I${Z_CHECKER_DIR}/include -I{ZFP_DIR}/include -I${MGARD_DIR}/include -I${FTK_DIR}/include -std=c++1z ${DEBUG}
LIBS=`adios2-config --cxx-libs` -L${SZ_DIR}/lib -lSZ -L${Z_CHECKER_DIR}/lib -lzc -L${ZFP_DIR}/lib -lzfp -L${MGARD_DIR}/lib -lmgard ${DEBUG}
CXX=mpicxx

compression: zchecker.o main.o ftk_3D.o
	$(CXX) zchecker.o main.o ftk_3D.o $(LIBS) -o compression

%.o: %.cpp $(DEPS)
	$(CXX) -c -o $@ $< $(CXXFLAGS)

clean:
	rm -f compression *~ *.o *.ps

