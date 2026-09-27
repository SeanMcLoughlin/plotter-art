import turtle

def apply_rules(axiom, rules, iterations):
    """Apply L-system rules for given number of iterations"""
    current = axiom
    for _ in range(iterations):
        next_string = ""
        for char in current:
            next_string += rules.get(char, char)
        current = next_string
    return current

def draw_lsystem_turtle(t, instructions, angle, distance):
    """Draw L-system using turtle graphics"""
    stack = []
    
    for cmd in instructions:
        if cmd == 'F':
            t.forward(distance)
        elif cmd == 'f':
            t.penup()
            t.forward(distance)
            t.pendown()
        elif cmd == '+':
            t.left(angle)
        elif cmd == '-':
            t.right(angle)
        elif cmd == '[':
            stack.append((t.position(), t.heading()))
        elif cmd == ']':
            position, heading = stack.pop()
            t.penup()
            t.setposition(position)
            t.setheading(heading)
            t.pendown()

# Set up the L-system
axiom = "-X"
rules = {
    'F': 'FF',
    'X': 'F+[[X]-X]-F[-FX]+X'
}
iterations = 6
angle = 24
distance = 2

# Generate the string
lsystem = apply_rules(axiom, rules, iterations)

# Set up turtle
screen = turtle.Screen()
screen.bgcolor("white")
screen.setup(800, 800)

t = turtle.Turtle()
t.speed(0)  # Fastest
t.hideturtle()
t.penup()
t.goto(0, -300)
t.setheading(90)
t.pendown()
t.pensize(1)
t.color("black")

# Draw the L-system
draw_lsystem_turtle(t, lsystem, angle, distance)

screen.exitonclick()
