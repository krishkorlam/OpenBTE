Point(0) = {-0.5,0.5,0,0.025};
Point(1) = {0.5,0.5,0,0.025};
Point(2) = {0.5,-0.5,0,0.025};
Point(3) = {-0.5,-0.5,0,0.025};
Line(0) = {0,1};
Line(1) = {1,2};
Line(2) = {2,3};
Line(3) = {3,0};
Line Loop(1) = {0,1,2,3};
Point(4) = {0.223606797749979,-0.22360679774997896,0,0.025};
Point(5) = {0.223606797749979,0.22360679774997896,0,0.025};
Point(6) = {-0.22360679774997896,0.223606797749979,0,0.025};
Point(7) = {-0.22360679774997902,-0.22360679774997896,0,0.025};
Line(4) = {4,5};
Line(5) = {5,6};
Line(6) = {6,7};
Line(7) = {7,4};
Line Loop(2) = {4,5,6,7};
Plane Surface(1)= {1,2};
Line Loop(3) = {-7,-6,-5,-4};
Plane Surface(2)= {3};
Physical Surface('Inclusion') = {2};
Physical Surface('Matrix') = {1};
Physical Line('Periodic_1') = {3};
Physical Line('Periodic_2') = {1};
Physical Line('Periodic_3') = {0};
Physical Line('Periodic_4') = {2};
Physical Line('Interface') = {4,5,6,7};
Periodic Line{3}={-1};
Periodic Line{2}={0};
