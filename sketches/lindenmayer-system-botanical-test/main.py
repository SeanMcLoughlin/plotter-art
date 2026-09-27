import matplotlib.pyplot as plt
import numpy as np

def apply_rules(axiom, rules, iterations):
    """Apply L-system rules for given number of iterations"""
    current = axiom
    for _ in range(iterations):
        next_string = ""
        for char in current:
            if char in rules:
                next_string += rules[char]
            else:
                next_string += char
        current = next_string
    return current

def draw_lsystem(instructions, angle, step_size):
    """Draw the L-system using turtle graphics logic"""
    # Initialize position and angle
    x, y = 0, 0
    current_angle = 90  # Start pointing up
    
    # Stack for saving/restoring state
    stack = []
    
    # Lists to store line segments
    lines = []
    current_line_x = [x]
    current_line_y = [y]
    
    for instruction in instructions:
        if instruction == 'F':
            # Move forward
            x += step_size * np.cos(np.radians(current_angle))
            y += step_size * np.sin(np.radians(current_angle))
            current_line_x.append(x)
            current_line_y.append(y)
            
        elif instruction == '+':
            # Turn left
            current_angle += angle
            
        elif instruction == '-':
            # Turn right
            current_angle -= angle
            
        elif instruction == '[':
            # Save state
            stack.append((x, y, current_angle, current_line_x.copy(), current_line_y.copy()))
            
        elif instruction == ']':
            # Restore state
            if current_line_x and len(current_line_x) > 1:
                lines.append((current_line_x, current_line_y))
            
            x, y, current_angle, current_line_x, current_line_y = stack.pop()
            current_line_x = [x]
            current_line_y = [y]
    
    # Add the last line segment
    if current_line_x and len(current_line_x) > 1:
        lines.append((current_line_x, current_line_y))
    
    return lines

# L-system parameters
n = 6
angle = 24
step_size = 1
axiom = "-X"
rules = {
    'F': 'FF',
    'X': 'F+[[X]-X]-F[-FX]+X'
}

# Generate the L-system string
lsystem_string = apply_rules(axiom, rules, n)

# Draw the L-system
lines = draw_lsystem(lsystem_string, angle, step_size)

# Create the plot
fig, ax = plt.subplots(figsize=(10, 12))

# Draw all line segments
for line_x, line_y in lines:
    ax.plot(line_x, line_y, 'k-', linewidth=0.5)

# Style the plot
ax.set_aspect('equal')
ax.axis('off')
ax.set_facecolor('white')
fig.patch.set_facecolor('white')

# Adjust margins
plt.tight_layout()
plt.show()

# Print some statistics
print(f"Final L-system string length: {len(lsystem_string)}")
print(f"Number of F commands: {lsystem_string.count('F')}")
print(f"Number of line segments drawn: {len(lines)}")
