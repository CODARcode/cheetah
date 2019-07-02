#include <vector>
#include <fstream>
#include <string>
#include "ftk_3D_interface.h"


void features2file(int step, std::string var, std::vector<critical_point_t>& v)
{
  std::ofstream f(var + "_" + std::to_string(step));
  for(int i = 0; i < v.size(); ++i)
    {
      for(int j = 0; j < 3; ++j)
	f << v[i].x[j] << " ";
      f << v[i].v;
      f << std::endl;
    }
  f.close();
}

