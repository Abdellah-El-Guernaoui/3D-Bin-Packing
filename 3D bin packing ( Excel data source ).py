import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF

def check_collision(box, placed_boxes):

    x, y, z = box['position']
    dx, dy, dz = box['dimensions']

    for other in placed_boxes:
        ox, oy, oz = other['position']
        odx, ody, odz = other['dimensions']

        if not (
            x + dx <= ox or  # Box is to the left
            x >= ox + odx or  # Box is to the right
            y + dy <= oy or  # Box is in front
            y >= oy + ody or  # Box is behind
            z + dz <= oz or  # Box is below
            z >= oz + odz    # Box is above
        ):
            return True  # Collision detected
    return False

def is_stable(box, placed_boxes):

    x, y, z = box['position']
    dx, dy, dz = box['dimensions']

    if z == 0:  # Box is on the ground
        return True

    # Check if the box is supported by any other box
    for other in placed_boxes:
        ox, oy, oz = other['position']
        odx, ody, odz = other['dimensions']

        if oz + odz == z:  # Other box is directly below

            if (odx >= dx and ody >= dy) and not (x + dx <= ox or x >= ox + odx or y + dy <= oy or y >= oy + ody):
                return True  # Box is supported
    return False  # Box is floating

def generate_rotations(box):

    dimensions = box['dimensions']
    rotations = [
        dimensions,
        (dimensions[1], dimensions[0], dimensions[2]),
        (dimensions[0], dimensions[2], dimensions[1]),
        (dimensions[2], dimensions[1], dimensions[0]),
    ]
    return [{'dimensions': rot, 'weight': box['weight']} for rot in rotations]

def find_placement_position(box, placed_boxes, container_dimensions):

    container_length, container_width, container_height = container_dimensions

    # Try all possible rotations
    for rotated_box in generate_rotations(box):
        box_length, box_width, box_height = rotated_box['dimensions']

        # Attempt to place the box at various positions
        for z in range(0, int(container_height - box_height) + 1):
            for y in range(0, int(container_width - box_width) + 1):
                for x in range(0, int(container_length - box_length) + 1):
                    rotated_box['position'] = (x, y, z)
                    if not check_collision(rotated_box, placed_boxes) and is_stable(rotated_box, placed_boxes):
                        return rotated_box  # Found a valid position

    return None  # No valid position found

def scatter_low_height_boxes(boxes, placed_boxes, container_dimensions):

    container_height = container_dimensions[2]

    for box in boxes:
        if box['dimensions'][2] < container_height * 0.3:  # Low-height box

            for other in placed_boxes:
                ox, oy, oz = other['position']
                odx, ody, odz = other['dimensions']

                box['position'] = (ox, oy, oz + odz)
                if not check_collision(box, placed_boxes) and is_stable(box, placed_boxes):
                    placed_boxes.append(box)
                    break
            else:
                placed_box = find_placement_position(box, placed_boxes, container_dimensions)
                if placed_box:
                    placed_boxes.append(placed_box)
        else:
            placed_box = find_placement_position(box, placed_boxes, container_dimensions)
            if placed_box:
                placed_boxes.append(placed_box)

def visualize_3d_bin_packing_with_weights(bins, bin_dimensions):
    fig = go.Figure()


    weights = [box['weight'] for box in bins]
    max_weight, min_weight = max(weights), min(weights)
    norm_weights = [(w - min_weight) / (max_weight - min_weight) for w in weights]

    # Define colorscale
    colorscale = ['#FF0000', '#FF7F00', '#FFFF00', '#7FFF00', '#00FF7F', '#00FFFF']
    colorbar_tickvals = [min_weight + (max_weight - min_weight) * i / (len(colorscale) - 1) for i in range(len(colorscale))]

    # Add boxes with color mapped to weight
    for i, box in enumerate(bins):
        x, y, z = box['position']
        dx, dy, dz = box['dimensions']
        weight = box['weight']
        color_index = norm_weights[i]
        color = colorscale[int(color_index * (len(colorscale) - 1))]

        # Define vertices of the cuboid
        vertices = [
            (x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z),  # Bottom face
            (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)  # Top face
        ]

        # Define cuboid faces
        faces = [
            [0, 1, 2, 3],  # Bottom face
            [4, 5, 6, 7],  # Top face
            [0, 1, 5, 4],  # Front face
            [2, 3, 7, 6],  # Back face
            [1, 2, 6, 5],  # Right face
            [0, 3, 7, 4]  # Left face
        ]

        # Add filled faces
        for face in faces:
            x_coords = [vertices[v][0] for v in face]
            y_coords = [vertices[v][1] for v in face]
            z_coords = [vertices[v][2] for v in face]

            fig.add_trace(go.Mesh3d(
                x=x_coords + [x_coords[0]],
                y=y_coords + [y_coords[0]],
                z=z_coords + [z_coords[0]],
                color=color,
                opacity=0.5,
                name=f"Box {i + 1}",
                hoverinfo="text",
                text=f"Box {i + 1}<br>Dimensions: {dx:.2f}x{dy:.2f}x{dz:.2f}<br>Weight: {weight:.2f} kg<br>Position: ({x:.2f}, {y:.2f}, {z:.2f})"
            ))

        # Add edges for the cuboid
        for face in faces:
            x_coords = [vertices[v][0] for v in face] + [vertices[face[0]][0]]
            y_coords = [vertices[v][1] for v in face] + [vertices[face[0]][1]]
            z_coords = [vertices[v][2] for v in face] + [vertices[face[0]][2]]

            fig.add_trace(go.Scatter3d(
                x=x_coords, y=y_coords, z=z_coords,
                mode='lines',
                line=dict(color=color, width=2),
                showlegend=False,
                hoverinfo="none"
            ))

    # Add a color scale bar
    fig.add_trace(go.Scatter3d(
        x=[None], y=[None], z=[None],
        mode='markers',
        marker=dict(
            size=15,
            color=weights,
            cmin=min_weight,
            cmax=max_weight,
            colorscale=colorscale,
            colorbar=dict(
                title="Weight (kg)",
                tickvals=colorbar_tickvals,
                ticktext=[f"{v:.1f}" for v in colorbar_tickvals],
                orientation='h',
                x=0.5,
                y=-0.1,
                len=0.5,
                thickness=20,
            ),
            showscale=True
        )
    ))

    # "Save PDF" button
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[None],
                        label="Save PDF",
                        method="update",
                        args2=[{"filename": "bin_packing_report.pdf"}],
                    )
                ],
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.1,
                yanchor="top"
            )
        ]
    )

    # Layout settings
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (ft)',
            yaxis_title='Width (ft)',
            zaxis_title='Height (ft)',
            aspectmode='manual',
            aspectratio=dict(x=bin_dimensions[0], y=bin_dimensions[1], z=bin_dimensions[2]),
        ),
        margin=dict(l=0, r=0, b=100, t=0),  # Adjust bottom margin for the color bar
        title="GIL's Packer Solver",
        title_x=0.5,  # Center the title
    )

    # Show the figure
    fig.show()

def generate_pdf_report(container_dimensions, placed_boxes, filename="bin_packing_report.pdf"):

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # title
    pdf.set_font("Arial", size=16, style="B")
    pdf.cell(200, 10, txt="GIL'S Packer Solver", ln=True, align="L")
    pdf.image("ENSAT logo.png", x=160, y=6, w=30)
    pdf.ln(20)

    # date
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="___ /___ / 20___", ln=True, align="C")
    pdf.ln(20)

    # Operator's ID
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(95, 10, txt="Operator's ID : ______________________________                Signature:", ln=0, align="L")
    pdf.ln(20)

    # project notes
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(200, 10, txt="Project Notes :", ln=True, align="L")
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="...............................................................................................................................................................", ln=True, align="L")
    pdf.ln(10)

    # container details
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(200, 10, txt="Details of the Container", ln=True, align="L")
    pdf.set_font("Arial", size=12)

    # Calculate container volume and occupied volume
    container_volume = container_dimensions[0] * container_dimensions[1] * container_dimensions[2]
    occupied_volume = sum(box['dimensions'][0] * box['dimensions'][1] * box['dimensions'][2] for box in placed_boxes)
    occupied_percentage = (occupied_volume / container_volume) * 100

    # table for container details
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(95, 10, txt="Dimensions", border=1, fill=True, align="C")
    pdf.cell(95, 10, txt="Capacity (ft³)", border=1, fill=True, align="C", ln=True)
    pdf.cell(95, 10, txt=f"{container_dimensions[0]}x{container_dimensions[1]}x{container_dimensions[2]}", border=1,
             align="C")
    pdf.cell(95, 10, txt=f"{container_volume:.2f}", border=1, align="C", ln=True)
    pdf.ln(10)

    # package details
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(200, 10, txt="Details of the Packages", ln=True, align="L")
    pdf.set_font("Arial", size=12)

    # table for package details
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(15, 10, txt="Item", border=1, fill=True, align="C")
    pdf.cell(20, 10, txt="Label", border=1, fill=True, align="C")
    pdf.cell(50, 10, txt="Dimensions (W x H x L)", border=1, fill=True, align="C")
    pdf.cell(30, 10, txt="Volume (ft³)", border=1, fill=True, align="C")
    pdf.cell(30, 10, txt="Weight (kg)", border=1, fill=True, align="C")
    pdf.cell(35, 10, txt="Notes", border=1, fill=True, align="C")
    pdf.cell(10, 10, txt="Q", border=1, fill=True, align="C", ln=True)

    for i, box in enumerate(placed_boxes):
        dimensions = box['dimensions']
        volume = dimensions[0] * dimensions[1] * dimensions[2]
        weight = box['weight']
        pdf.cell(15, 10, txt=f"Box {i+1}", border=1, align="C")
        pdf.cell(20, 10, txt=f"Label {i+1}", border=1, align="C")
        pdf.cell(50, 10, txt=f"{dimensions[0]:.2f}x{dimensions[1]:.2f}x{dimensions[2]:.2f}", border=1, align="C")
        pdf.cell(30, 10, txt=f"{volume:.2f}", border=1, align="C")
        pdf.cell(30, 10, txt=f"{weight:.2f}", border=1, align="C")
        pdf.cell(35, 10, txt="", border=1, align="C")
        pdf.cell(10, 10, txt="1", border=1, align="C", ln=True)

    # space calculation table
    pdf.ln(10)
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(200, 10, txt="Space Utilization", ln=True, align="L")
    pdf.set_font("Arial", size=12)

    # space taken and remaining
    space_taken = occupied_volume
    space_remaining = container_volume - space_taken

    # space utilization
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(95, 10, txt="Space Taken (ft³)", border=1, fill=True, align="C")
    pdf.cell(95, 10, txt="Space Remaining (ft³)", border=1, fill=True, align="C", ln=True)
    pdf.cell(95, 10, txt=f"{space_taken:.2f}", border=1, align="C")
    pdf.cell(95, 10, txt=f"{space_remaining:.2f}", border=1, align="C", ln=True)

    # Save the PDF
    pdf.output(filename)
    print(f"PDF report saved as {filename}")

def read_packages_from_excel(file_path):

    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        print("Columns in the Excel file:", df.columns)  # Debugging: Print column names

        packages = []
        for _, row in df.iterrows():
            # Use the exact column names from the Excel file
            width = row['Width ( W )']
            height = row['Height ( H )']
            length = row['Length ( L )']
            quantity = row['Quantity ( Q )']
            weight = row['Weight ( kg )']  # make sure they match the columns names
            for _ in range(int(quantity)):
                packages.append({
                    'dimensions': (width, height, length),
                    'weight': weight
                })
        return packages
    except KeyError as e:
        print(f"Error: Column '{e.args[0]}' not found in the Excel file. Please check the column names.")
        exit()
    except Exception as e:
        print(f"An error occurred while reading the Excel file: {e}")
        exit()

# Generate and place boxes
if __name__ == "__main__":
    container_dimensions = (40, 8, 8.5)

    file_path = "Package's Sheet.xlsx"

    packages = read_packages_from_excel(file_path)

    placed_boxes = []
    scatter_low_height_boxes(packages, placed_boxes, container_dimensions)

    visualize_3d_bin_packing_with_weights(placed_boxes, container_dimensions)

    generate_pdf_report(container_dimensions, placed_boxes)