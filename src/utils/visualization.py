import plotly.graph_objects as go
from .constants import STANDARD_BOXES

def get_box_type_from_name(name):
    return name.split('_')[0]

def get_cube_vertices_and_faces(pos, dims):
    vertices = [
        [pos[0], pos[1], pos[2]],
        [pos[0]+dims[0], pos[1], pos[2]],
        [pos[0]+dims[0], pos[1]+dims[1], pos[2]],
        [pos[0], pos[1]+dims[1], pos[2]],
        [pos[0], pos[1], pos[2]+dims[2]],
        [pos[0]+dims[0], pos[1], pos[2]+dims[2]],
        [pos[0]+dims[0], pos[1]+dims[1], pos[2]+dims[2]],
        [pos[0], pos[1]+dims[1], pos[2]+dims[2]]
    ]
    faces = [
        [0, 1, 2], [0, 2, 3],  # нижняя грань
        [4, 5, 6], [4, 6, 7],  # верхняя грань
        [0, 1, 5], [0, 5, 4],  # передняя грань
        [2, 3, 7], [2, 7, 6],  # задняя грань
        [0, 3, 7], [0, 7, 4],  # левая грань
        [1, 2, 6], [1, 6, 5]   # правая грань
    ]
    return vertices, faces

def create_mesh_trace_with_edges(vertices, faces, color, opacity, name):
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]
    i = [f[0] for f in faces]
    j = [f[1] for f in faces]
    k = [f[2] for f in faces]
    
    mesh = go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        opacity=opacity,
        color=color,
        name=name,
        flatshading=True
    )
    
    lines_x = []
    lines_y = []
    lines_z = []
    edges = [
        (0,1), (1,2), (2,3), (3,0),  # нижняя грань
        (4,5), (5,6), (6,7), (7,4),  # верхняя грань
        (0,4), (1,5), (2,6), (3,7)   # вертикальные ребра
    ]
    
    for edge in edges:
        lines_x.extend([vertices[edge[0]][0], vertices[edge[1]][0], None])
        lines_y.extend([vertices[edge[0]][1], vertices[edge[1]][1], None])
        lines_z.extend([vertices[edge[0]][2], vertices[edge[1]][2], None])
    
    lines = go.Scatter3d(
        x=lines_x,
        y=lines_y,
        z=lines_z,
        mode='lines',
        line=dict(color='black', width=2),
        name=f'{name} edges',
        showlegend=False
    )
    
    return mesh, lines

def create_pallet_trace(dims):
    vertices = [
        [0, 0, 0],
        [dims[0], 0, 0],
        [dims[0], dims[1], 0],
        [0, dims[1], 0]
    ]
    faces = [[0, 1, 2], [0, 2, 3]]
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]
    i = [f[0] for f in faces]
    j = [f[1] for f in faces]
    k = [f[2] for f in faces]
    return go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        opacity=0.5,
        color='gray',
        name='Поддон'
    )

def create_3d_visualization(packer):
    fig = go.Figure()
    bin_dims = [packer.bins[0].width, packer.bins[0].height, packer.bins[0].depth]
    pallet_trace = create_pallet_trace(bin_dims)
    fig.add_trace(pallet_trace)
    
    # Цвета для пользовательских коробок
    custom_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan']
    custom_box_colors = {}
    color_index = 0
    
    sorted_items = sorted(
        packer.bins[0].items,
        key=lambda x: x.position[2]
    )
    
    for item in sorted_items:
        pos = [item.position[0], item.position[1], item.position[2]]
        dims = [item.width, item.height, item.depth]
        box_type = get_box_type_from_name(item.name)
        
        # Получаем цвет из STANDARD_BOXES или назначаем новый для типа коробки
        if box_type in STANDARD_BOXES:
            color = STANDARD_BOXES[box_type]['color']
        else:
            if box_type not in custom_box_colors:
                custom_box_colors[box_type] = custom_colors[color_index % len(custom_colors)]
                color_index += 1
            color = custom_box_colors[box_type]
            
        vertices, faces = get_cube_vertices_and_faces(pos, dims)
        box_mesh, box_edges = create_mesh_trace_with_edges(
            vertices, faces, color, 0.7, f'Коробка {item.name}'
        )
        
        fig.add_trace(box_mesh)
        fig.add_trace(box_edges)

    fig.update_layout(
        scene=dict(
            aspectmode='cube',
            xaxis=dict(nticks=4, range=[0, bin_dims[0]], title='Длина'),
            yaxis=dict(nticks=4, range=[0, bin_dims[1]], title='Ширина'),
            zaxis=dict(nticks=4, range=[0, bin_dims[2]], title='Высота'),
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=2, y=2, z=2)
            )
        ),
        title="3D визуализация упаковки",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )
    
    return fig