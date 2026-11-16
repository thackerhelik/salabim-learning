import salabim as sim

env = sim.Environment()
env.animate(True)
env.modelname("Demo animation classes")
# env.background_color("90%gray")

# Class AnimateLine
# sim.AnimateLine(spec = (0, 100, 0, 500, 100, 500, 200, 300, 100, 100), linecolor='red', angle=-10, linewidth=10) #, as_points=True)

# Class AnimatePoints
# sim.AnimatePoints(spec = (0, 100, 0, 500, 100, 500, 200, 300, 100, 100), linecolor='red', angle=-10, linewidth=10) #, as_points=False)

# Class AnimatePolygon
# sim.AnimatePolygon(spec = (0, 100, 0, 500, 100, 500, 200, 300, 100, 100), linecolor='red', fillcolor='blue', angle=-10, linewidth=10)

# Class AnimateRectangle
# sim.AnimateRectangle(spec = (0, 100, 200, 600), linecolor="red", fillcolor="", angle=-10, linewidth=10)

# Class AnimateCircle
# sim.AnimateCircle(radius=75, x = 100, y=100, linecolor="red", fillcolor="pink", linewidth=5, arc_angle0=0, arc_angle1=315, draw_arc=True)

# Class AnimateImage
# sim.AnimateImage(image="hiking.png", angle=-10, alpha=100)

# Class AnimateText
# sim.AnimateText(text="Hello world", x=100, y=100, font="Chalkduster", angle=-10, textcolor="red") #, text_anchor="c")

# Class Animate - only one type allowed per instance of Animate
# sim.Animate(t1=env.now()+10,x0=100,y0=100,x1=200,y1=0,rectangle0=(-10,-10,10,10))
# sim.Animate(t1=env.now()+10,x0=100,y0=100,x1=200,y1=0,rectangle0=(-10,-10,10,10),rectangle1=(-20,-20,20,20), keep=False) # keep=False object disappers after t1
# sim.Animate(t1=env.now()+10,text='Test',x0=250,y0=250,x1=250,y1=250,textcolor0='red',textcolor1='blue',angle0=0,angle1=360)

## Update Animation
# Part 1
# an=sim.Animate(t0=0,t1=10,x0=50,x1=150,y0=50,circle0=10,circle1=20)

# class Updater(sim.Component):
#     def process(self):
#         self.hold(5)
#         an.update(t1=10,y1=100,circle1=10)

# Updater()

# Part 2
# class AnimateMovingText(sim.Animate):
#     def __init__(self):
#         sim.Animate.__init__(self, text="", x0=100, x1=1000, t1=env.now()+10)

#     def y(self, t):
#         return int(t) * 50 + 20

#     def text(self, t):
#         return f"{t:0.1f}"

# AnimateMovingText()


# Layers
# sim.AnimateRectangle(spec=(0, 0, 200, 200), fillcolor="blue", text="layer-1", layer=-1)
# sim.AnimateRectangle(spec=(150, 150, 350, 350), fillcolor="red", text="layer0")#, layer=0) - default is 0 anyway
# sim.AnimateRectangle(spec=(300, 300, 500, 500), fillcolor="green", text="layer1", layer=1)

# Colors
# env.show_time(False)
# env.background_color("90%gray")

# for i, name in enumerate(sorted(env.colornames())):
#     x = 7 + (i%6) * 170
#     y = 720 - (i // 6) * 28
#     env.AnimateRectangle(
#         (0, 0, 160, 21),
#         x=x,
#         y=y,
#         fillcolor=name,
#         text=(name, "<null string>")[name == ""],
#         textcolor=("black", "white")[env.is_dark(name)],
#         font="calibribold",
#         fontsize=17,
#         linecolor="black",
#     )


# # using animated images
# class X(sim.Component):
#     def animation_objects1(self):
#         an1 = env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=50, offsety=-15)
#         an2 = env.AnimateImage(text=f"{self.sequence_number()}", offsetx=15, offsety=-25, fontsize=13)
#         return 50, 50, an1, an2

#     def process(self):
#         self.enter(env.q)
#         self.hold(env.Uniform(5))
#         self.leave(env.q)

class X(sim.Component):
    def animation_objects(self):
        an1 = env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=50, offsety=-15)
        an2 = env.AnimateText(text=f"{self.sequence_number()}", offsetx=15, offsety=-25, fontsize=13)
        return 50, 50, an1, an2

    def process(self):
        self.enter(env.q)
        self.hold(env.Uniform(5))
        self.leave(env.q)

env.speed(3)
env.background_color(("#eeffcc"))
env.width(1000, True)
env.height(700)
env.animate(True)

env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=150, x=lambda t: 1000 - 30 * t, y=150)
env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=300, x=lambda t: 1000 - 60 * t, y=220)
env.AnimateImage(
    "https://salabim.org/bird.gif",
    animation_repeat=True,
    width=100,
    animation_speed=1.5,
    x=lambda t: 0 + 100 * (t - 25),
    y=350,
    animation_start=25,
    flip_horizontal=True,
)
env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=240, animation_speed=0.5, x=lambda t: 1000 - 50 * t, y=380)
env.AnimateImage("https://salabim.org/bird.gif", animation_repeat=True, width=250, animation_speed=1.3, x=lambda t: 1000 - 40 * t, y=480)


env.q = env.Queue("queue")
env.q.animate(x=700, y=50, direction="w")
env.ComponentGenerator(X, iat=env.Exponential(1.5))

env.run()

# with env.video("birds.mp4"):
#     env.run(35)