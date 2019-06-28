/*
  Based on https://github.com/CODARcode/ftk/blob/master/examples/critical_point_tracking_3d/ex_critical_point_tracking_3d.cpp
 */

#include <fstream>
#include <mutex>
#include <cassert>

#include <ftk/numeric/print.hh>
#include <ftk/numeric/cross_product.hh>
#include <ftk/numeric/vector_norm.hh>
#include <ftk/numeric/linear_interpolation.hh>
#include <ftk/numeric/bilinear_interpolation.hh>
#include <ftk/numeric/inverse_linear_interpolation_solver.hh>
#include <ftk/numeric/inverse_bilinear_interpolation_solver.hh>
#include <ftk/numeric/gradient.hh>
#include <ftk/algorithms/cca.hh>
#include <ftk/geometry/cc2curves.hh>
#include <ftk/geometry/curve2tube.hh>
#include <hypermesh/ndarray.hh>
#include <hypermesh/regular_simplex_mesh.hh>

#include <functional>

#include "ftk_3D_interface.h"

std::mutex mutex;

void derive_gradients(const size_t DW, const size_t DH, const size_t DD,
		      const hypermesh::ndarray<double> &scalar,
		      hypermesh::ndarray<double> & grad)
{
  fprintf(stderr, "deriving gradients...\n");
  grad.reshape({3, DW, DH, DD});
  for (int k = 1; k < DD-1; k ++) {
    for (int j = 1; j < DH-1; j ++) {
      for (int i = 1; i < DW-1; i ++) {
        grad(0, i, j, k) = 0.5 * (scalar(i+1, j, k) - scalar(i-1, j, k));
        grad(1, i, j, k) = 0.5 * (scalar(i, j+1, k) - scalar(i, j-1, k));
        grad(2, i, j, k) = 0.5 * (scalar(i, j, k+1) - scalar(i, j, k-1));
      }
    }
  }
}


void derive_hessians(const size_t DW, const size_t DH, const size_t DD,
		     const hypermesh::ndarray<double> & grad,
		     hypermesh::ndarray<double> & hess)
{
  fprintf(stderr, "deriving hessians...\n");
  hess.reshape({3, 3, DW, DH, DD});

  for (int k = 2; k < DD-2; k ++) {
    for (int j = 2; j < DH-2; j ++) {
      for (int i = 2; i < DW-2; i ++) {
        const double H00 = hess(0, 0, i, j, k) = // ddf/dx2
          0.5 * (grad(0, i+1, j, k) - grad(0, i-1, j, k));
        const double H01 = hess(0, 1, i, j, k) = // ddf/dxdy
          0.5 * (grad(0, i, j+1, k) - grad(0, i, j-1, k));
        const double H02 = hess(0, 2, i, j, k) = // ddf/dxdz
          0.5 * (grad(0, i, j, k+1) - grad(0, i, j, k-1));

        const double H10 = hess(1, 0, i, j, k) = // ddf/dydx
          0.5 * (grad(1, i+1, j, k) - grad(1, i-1, j, k));
        const double H11 = hess(1, 1, i, j, k) = // ddf/dy2
          0.5 * (grad(1, i, j+1, k) - grad(1, i, j-1, k));
        const double H12 = hess(1, 2, i, j, k) = // ddf/dydz
          0.5 * (grad(1, i, j, k+1) - grad(1, i, j, k-1));

        const double H20 = hess(2, 0, i, j, k) = // ddf/dydx
          0.5 * (grad(2, i+1, j, k) - grad(2, i-1, j, k));
        const double H21 = hess(2, 1, i, j, k) = // ddf/dy2
          0.5 * (grad(2, i, j+1, k) - grad(2, i, j-1, k));
        const double H22 = hess(2, 2, i, j, k) = // ddf/dydz
          0.5 * (grad(2, i, j, k+1) - grad(2, i, j, k-1));
      }
    }
  }
}

void check_simplex(const hypermesh::regular_simplex_mesh_element& s,
		   std::map<hypermesh::regular_simplex_mesh_element, critical_point_t> & critical_points,
		   hypermesh::ndarray<double> & scalar,
		   hypermesh::ndarray<double> & grad,
		   hypermesh::ndarray<double> & hess
		   )
{
  if (!s.valid()) return; // check if the 3-simplex is valid
  // fprintf(stderr, "%zu\n", s.to_integer());

  const auto &vertices = s.vertices();
  double X[4][4], g[4][3], value[4];

  for (int i = 0; i < 4; i ++) {
    for (int j = 0; j < 3; j ++)
      g[i][j] = grad(j, vertices[i][0], vertices[i][1], vertices[i][2]); // , vertices[i][3]);
    for (int j = 0; j < 4; j ++)
      X[i][j] = vertices[i][j];
    value[i] = scalar(vertices[i][0], vertices[i][1], vertices[i][2]); // , vertices[i][3]);
  }

  // check intersection
  double mu[4], x[3];
  bool succ = ftk::inverse_lerp_s3v3(g, mu);
  if (!succ) return;

  // check hessian
  double H[4][3][3], h[3][3];
  for (int i = 0; i < 4; i ++)
    for (int j = 0; j < 3; j ++)
      for (int k = 0; k < 3; k ++)
        H[i][j][k] = hess(j, k, vertices[i][0], vertices[i][1], vertices[i][2]); // , vertices[i][3]);
  ftk::lerp_s3m3x3(H, mu, h);

  double eig[3];
  ftk::solve_eigenvalues_symmetric3x3(h, eig);
  // fprintf(stderr, "eig=%f, %f, %f\n", eig[0], eig[1], eig[2]);

  if (eig[0] < 0 && eig[1] < 0 && eig[2] < 0) { // local maxima
    // dump results
    double val = ftk::lerp_s3(value, mu);
    ftk::lerp_s3v4(X, mu, x);
   
    critical_point_t p;
    
    p.x[0] = x[0]; p.x[1] = x[1]; p.x[2] = x[2]; // p.x[3] = x[3];
    p.v = val;
    {
      std::lock_guard<std::mutex> guard(mutex);
      critical_points[s] = p;
    
      std::cerr << s << std::endl;
      fprintf(stderr, "x={%f, %f, %f}\n", x[0], x[1], x[2]); // , x[3]);
    }
  }
}

void extract_critical_points(const size_t DW, const size_t DH, const size_t DD,
			     std::map<hypermesh::regular_simplex_mesh_element, critical_point_t> & critical_points,
			     hypermesh::ndarray<double> & scalar,
			     hypermesh::ndarray<double> & grad,
			     hypermesh::ndarray<double> & hess,
			     hypermesh::regular_simplex_mesh & m
			     )
{
  using namespace std::placeholders;
  fprintf(stderr, "extracting critical points...\n");
  m.set_lb_ub({2, 2, 2}, {static_cast<int>(DW)-3,
	static_cast<int>(DH)-3, static_cast<int>(DD)-3}); // set the lower and upper bounds of the mesh
  auto my_check_simplex = std::bind(check_simplex,_1, std::ref(critical_points),
				    std::ref(scalar), std::ref(grad), std::ref(hess)); 
  m.element_for(3, my_check_simplex); // iterate over all 3-simplices
}

// public interface to ftk
std::vector<critical_point_t> extract_features(double *data, const size_t DW,
					       const size_t DH, const size_t DD)
{
  hypermesh::ndarray<double> scalar, grad, hess;
  hypermesh::regular_simplex_mesh m(3); // the 3D spatial mesh
  std::map<hypermesh::regular_simplex_mesh_element, critical_point_t> critical_points;


  size_t starts[4] = {0, 0, 0, 0}, 
         sizes[4]  = {1, size_t(DD), size_t(DH), size_t(DW)};

  scalar.reshape({DW, DH, DD});

  // can one avoid copying? data comes from a vector,
  // scalar under the hood is a vector
  for (int k = 0; k < DD; k ++)
    for (int j = 0; j < DH; j ++)
      for (int i = 0; i < DW; i ++)
        scalar(i, j, k) = data[i*DW*DH + j*DW + k];
  
  derive_gradients(DW, DH, DD, scalar, grad);
  derive_hessians(DW, DH, DD, grad, hess);
  
  extract_critical_points(DW, DH, DD, critical_points, scalar, grad, hess, m);

  std::vector<critical_point_t> features;
  for(auto cp = critical_points.begin(); cp != critical_points.end(); ++cp)
    features.push_back(cp->second);
  return features;
}

void distance_between_features(std::vector<critical_point_t>& features1,
			       std::vector<critical_point_t>& features2,
			       int * difference, double * normalized)
{
  double norm = (features1.size() + features2.size())/2;
  if(norm == 0.0)
    {
      *difference = 0;
      *normalized = 0.0;
    }
  else
    {
      *difference = features1.size() - features2.size();
      *normalized = *difference/norm;
    }
}
