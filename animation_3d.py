import salabim as sim

env = sim.Environment()
env.background_color("90%gray")

# Set position and size of 2D window
env.width(900)
env.height(700)
env.position((1000, 0))

# Set position and size of 3D window
env.width3d(900)
env.height3d(700)
env.position3d((0, 100))

env.animate3d(True)
env.animate(True) # If want to show both 2d and 3d

env.show_camera_position()
env.show_camera_position(over3d=True)

sim.Animate3dGrid(x_range=range(-2,3), y_range=range(-2,3))
traj0 = sim.TrajectoryCircle(radius=2, vmax=1)
d0 = traj0.duration()
sim.Animate3dBox(x_len=1, y_len=1, z_len=1, color="red", x=lambda t: traj0.x(t%d0), y=lambda t: traj0.y(t%d0), z=0.5, z_angle=lambda t: traj0.angle(t%d0))

traj1 = sim.TrajectoryCircle(radius=1, vmax=1, angle0=360, angle1=0)
d1 = traj1.duration()
sim.Animate3dBox(x_len=0.5, y_len=0.5, z_len=0.5, color="green", x=lambda t: traj1.x(t%d1), y=lambda t: traj1.y(t%d1), z=0.25, z_angle=lambda t: traj1.angle(t%d1))

env.camera_move("""\
view(x_eye=4.0000,y_eye=4.0000,z_eye=4.0000,x_center=0.0000,y_center=0.0000,z_center=0.0000,field_of_view_y=45.0000)  # t=0.0000
view(x_eye=3.6000,y_eye=3.6000,z_eye=3.6000)  # t=0.4957
view(x_eye=3.2400,y_eye=3.2400,z_eye=3.2400)  # t=0.9443
view(x_eye=3.2961,y_eye=3.1830)  # t=1.6593
view(x_eye=3.2961,y_eye=3.1830,z_eye=2.9160)  # t=3.3829
view(x_eye=3.2961,y_eye=3.1830,z_eye=2.6244)  # t=3.5666
view(x_eye=3.2961,y_eye=3.1830,z_eye=2.3620)  # t=3.7464
view(x_eye=3.2961,y_eye=3.1830,z_eye=2.1258)  # t=3.8976
view(x_eye=3.2961,y_eye=3.1830,z_eye=1.9132)  # t=4.1154
view(x_eye=3.2961,y_eye=3.1830,z_eye=1.7219)  # t=4.3627
view(x_eye=3.2961,y_eye=3.1830,z_eye=1.5497)  # t=4.5476
view(x_eye=3.2961,y_eye=3.1830,z_eye=1.3947)  # t=4.7275
view(x_eye=3.3511,y_eye=3.1250)  # t=5.3634
view(field_of_view_y=40.5000)  # t=6.4102
view(field_of_view_y=36.4500)  # t=6.7709
view(field_of_view_y=40.5000)  # t=7.2002
view(field_of_view_y=45.0000)  # t=7.3853
view(field_of_view_y=50.0000)  # t=7.5354
view(field_of_view_y=55.5556)  # t=7.6858
view(field_of_view_y=61.7284)  # t=7.8731
view(field_of_view_y=68.5871)  # t=8.0212
view(field_of_view_y=76.2079)  # t=8.2113
view(field_of_view_y=84.6754)  # t=8.4003
view(field_of_view_y=94.0838)  # t=8.5829
view(field_of_view_y=104.5376)  # t=8.7949
view(field_of_view_y=116.1529)  # t=9.0388
view(field_of_view_y=129.0587)  # t=9.2250
view(field_of_view_y=143.3986)  # t=9.4486
view(field_of_view_y=129.0587)  # t=11.0184
view(x_eye=4.0000,y_eye=4.0000,z_eye=4.0000,x_center=0.0000,y_center=0.0000,z_center=0.0000,field_of_view_y=45.0000)  # t=11.6400
   """, lag=1)

env.run(sim.inf)