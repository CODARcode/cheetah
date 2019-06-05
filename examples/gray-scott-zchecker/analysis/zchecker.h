#ifndef ZCHECKER_H
#define ZCHECKER_H

#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <cstdint>
#include <cmath>
#include <chrono>
#include <string>
#include <thread>
#include <cassert>
#include "sz.h"
#include "adios2.h"
#include "zc.h"
#include "zfp.h"
extern "C" {
#include "mgard_capi.h"
}

void printUsage();
void z_check_mgard(int stepAnalysis, std::vector<double>& u, const std::string &solution,
		   const std::vector<std::size_t>& shape);
void z_check_zfp(int stepAnalysis, std::vector<double>& u, const std::string &solution);
double * z_check_sz(int stepAnalysis, std::vector<double>& u,
			      const std::string &solution,
			      const std::vector<std::size_t>& shape);
#endif
