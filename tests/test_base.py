# tests/test_base.py
import pytest
from py3dbp import Bin, Item
from src.packers.weight_aware import WeightAwarePacker
from src.packers.extreme_points import ExtremePointPacker
from src.packers.laff import LAFFPacker
from src.packers.corner_points import CornerPointPacker
from src.packers.sfc import SFCPacker

# Фикстуры
@pytest.fixture
def standard_bin():
    return Bin('test_pallet', 120, 80, 160, 1000)

@pytest.fixture
def small_box():
    return Item('small_box', 20, 15, 10, 2)

@pytest.fixture
def medium_box():
    return Item('medium_box', 30, 20, 15, 5)

@pytest.fixture
def large_box():
    return Item('large_box', 40, 30, 20, 10)

# Базовые тесты
def test_bin_dimensions(standard_bin):
    assert standard_bin.width == 120
    assert standard_bin.height == 80
    assert standard_bin.depth == 160
    assert standard_bin.max_weight == 1000

def test_box_dimensions(small_box):
    assert small_box.width == 20
    assert small_box.height == 15
    assert small_box.depth == 10
    assert small_box.weight == 2

# Тесты WeightAwarePacker
def test_weight_aware_basic_packing(standard_bin, small_box):
    packer = WeightAwarePacker()
    packer.add_bin(standard_bin)
    packer.add_item(small_box)
    packer.pack()
    
    assert len(packer.bins[0].items) == 1
    assert len(packer.unpacked_items) == 0
    assert packer.bins[0].items[0].position == [0, 0, 0]

def test_weight_support(standard_bin):
    packer = WeightAwarePacker()
    packer.add_bin(standard_bin)
    
    heavy_box = Item('heavy_box', 30, 30, 30, 50)
    light_box = Item('light_box', 30, 30, 30, 5)
    
    packer.add_item(heavy_box)
    packer.add_item(light_box)
    packer.pack()
    
    # Проверяем, что тяжелая коробка внизу
    assert packer.bins[0].items[0].weight > packer.bins[0].items[1].weight

# Тесты ExtremePointPacker
def test_extreme_points_packing(standard_bin, small_box, medium_box):
    packer = ExtremePointPacker()
    packer.add_bin(standard_bin)
    packer.add_item(small_box)
    packer.add_item(medium_box)
    packer.pack()
    
    assert len(packer.bins[0].items) == 2
    assert len(packer.unpacked_items) == 0

# Тесты LAFFPacker
def test_laff_layer_packing(standard_bin, small_box, medium_box):
    packer = LAFFPacker()
    packer.add_bin(standard_bin)
    packer.add_item(small_box)
    packer.add_item(medium_box)
    packer.pack()
    
    assert len(packer.bins[0].items) == 2
    assert len(packer.unpacked_items) == 0

# Тесты CornerPointPacker
def test_corner_points_packing(standard_bin, small_box):
    packer = CornerPointPacker()
    packer.add_bin(standard_bin)
    packer.add_item(small_box)
    packer.pack()
    
    assert len(packer.bins[0].items) == 1
    assert len(packer.unpacked_items) == 0

# Тесты SFCPacker
def test_sfc_packing(standard_bin, small_box):
    packer = SFCPacker()
    packer.add_bin(standard_bin)
    packer.add_item(small_box)
    packer.pack()
    
    assert len(packer.bins[0].items) == 1
    assert len(packer.unpacked_items) == 0

# Тесты пересечений
def test_intersection_prevention():
    packer = WeightAwarePacker()
    bin = Bin('test_pallet', 120, 80, 160, 1000)
    packer.add_bin(bin)
    
    box1 = Item('box1', 30, 30, 30, 10)
    box2 = Item('box2', 30, 30, 30, 10)
    
    packer.add_item(box1)
    packer.add_item(box2)
    packer.pack()
    
    # Проверяем отсутствие пересечений
    for item1 in packer.bins[0].items:
        for item2 in packer.bins[0].items:
            if item1 != item2:
                assert not packer._check_intersection(
                    item1, 
                    item2, 
                    item1.position[0],
                    item1.position[1],
                    item1.position[2]
                )

# Тесты граничных случаев
def test_edge_cases(standard_bin):
    packer = WeightAwarePacker()
    packer.add_bin(standard_bin)
    
    # Тест очень большой коробки
    huge_box = Item('huge_box', 130, 90, 170, 50)
    packer.add_item(huge_box)
    packer.pack()
    
    # Проверяем, что коробка не была упакована
    assert len(packer.bins[0].items) == 0
    assert len(packer.unpacked_items) == 1
    assert packer.unpacked_items[0].name == 'huge_box'
