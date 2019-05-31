DEPS=zchecker.h
CXXFLAGS=`adios2-config --cxx-flags` -I${SZ_DIR}/include -I${Z_CHECKER_DIR}/include -I{ZFP_DIR}/include -I${MGARD_DIR}/include
LIBS=`adios2-config --cxx-libs` -L${SZ_DIR}/lib -lSZ -L${Z_CHECKER_DIR}/lib -lzc -L${ZFP_DIR}/lib -lzfp -L${MGARD_DIR}/lib -lmgard
CXX=mpicxx

zchecker: zchecker.o main.o
	$(CXX) zchecker.o main.o $(LIBS) -o zchecker

%.o: %.cpp $(DEPS)
	$(CXX) -c -o $@ $< $(CXXFLAGS)

clean:
	rm -f a.out zchecker *~ *.o *.ps

