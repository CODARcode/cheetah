#ifndef FTK_3D_INTERFACE_H
#define FTK_3D_INTERFACE_H

struct critical_point_t {
  float x[3]; // the spacetime coordinates of the trajectory                                                                                                                        
  double v;
};

std::vector<critical_point_t> extract_features(double *data, const size_t DW,
					       const size_t DH, const size_t DD);

void distance_between_features(std::vector<critical_point_t>& features1,
                                 std::vector<critical_point_t>& features2,
				 int * difference, double * normalized);


#endif
