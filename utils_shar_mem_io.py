# Credit goes to Lucas Cardellini for figuring out all the addresses and offsets for SMIO_read()
# SMIO_write

from pymem import Pymem
from mathutils import Vector, Matrix
from math import degrees,radians

Versions_dict = {
    1267409524:"ReleaseEnglish",
    4209509573:"Demo",
    3380997427:"ReleaseInternational",
    4232482053:"BestSellerSeries",
}

def SMIO_read():
    try:
        SHAR = Pymem('Simpsons.exe')
    except:
        return

    SMIO_info = {}

    SMIO_info['Version'] = Version = Versions_dict[SHAR.read_int(0x593FFF)]
        
    def VersionSelect(ReleaseEnglishAddress, DemoAddress, ReleaseInternationalAddress, BestSellerSeriesAddress):
        if Version == "ReleaseEnglish":
            return ReleaseEnglishAddress
        if Version == "Demo":
            return DemoAddress
        if Version == "ReleaseInternational": 
            return ReleaseInternationalAddress
        if Version == "BestSellerSeries":
            return BestSellerSeriesAddress


    def GameFlow():
        return SHAR.read_int(VersionSelect(0x6C9014, 0x6C8FD4, 0x6C8FD4, 0x6C900C))
    
    GameStates = [
            "PreLicence",
            "Licence",
            "MainMenu",
            "DemoLoading",
            "DemoInGame",
            "BonusSetup",
            "BonusLoading",
            "BonusInGame",
            "NormalLoading",
            "NormalInGame",
            "NormalPaused",
            "Exit"
    ]

    def GameState(GameFlow):
        if GameFlow == 0:
            return 0
        else:
            return GameStates[SHAR.read_int(GameFlow+0xC)]
    
    SMIO_info['GameState'] = GameState = GameState(GameFlow())

    def CharacterPosition(Character):
        Offset = Character + 0x64
        v = Vector((SHAR.read_float(Offset), SHAR.read_float(Offset + 0x4), SHAR.read_float(Offset + 0x8)))
        v.y,v.z = v.z,v.y
        return v

    def CharacterManager():
        return SHAR.read_int(VersionSelect(0x6C8470, 0x6C8430, 0x6C8430, 0x6C8468))

    def Characters(CharacterManager, Index):
        return SHAR.read_int(CharacterManager + 0xC0 + Index * 0x4)

    def CharacterRotation(Character):
        return SHAR.read_float(Character + 0x110)

    def CharacterInCar(Character):
        return SHAR.read_int(Character + 0x15C) != 0

    def CharacterName(CharacterManager, Index):
        return SHAR.read_string(CharacterManager + 0x1C0 + Index * 0x40, 64)

    def CharacterCar(Character):
        return SHAR.read_int(Character + 0x15C)        

    def CarPosRot(Car):
        Offset = Car + 0xB8
        m = [
            [SHAR.read_float(Offset),           SHAR.read_float(Offset + 0x4),  SHAR.read_float(Offset + 0x8),  SHAR.read_float(Offset + 0xC)],
            [SHAR.read_float(Offset + 0x10),    SHAR.read_float(Offset + 0x14), SHAR.read_float(Offset + 0x18), SHAR.read_float(Offset + 0x1C)],
            [SHAR.read_float(Offset + 0x20),    SHAR.read_float(Offset + 0x24), SHAR.read_float(Offset + 0x28), SHAR.read_float(Offset + 0x2C)],
            [SHAR.read_float(Offset + 0x30),    SHAR.read_float(Offset + 0x34), SHAR.read_float(Offset + 0x38), SHAR.read_float(Offset + 0x3C)]
            ]
        rot = [
            [SHAR.read_float(Offset),           SHAR.read_float(Offset + 0x4),    SHAR.read_float(Offset + 0x8)],
            [SHAR.read_float(Offset + 0x10),    SHAR.read_float(Offset + 0x14),   SHAR.read_float(Offset + 0x18)],
            [SHAR.read_float(Offset + 0x20),    SHAR.read_float(Offset + 0x24),   SHAR.read_float(Offset + 0x28)],
            ]
        rot = Matrix(rot).to_quaternion()
        rot.y,rot.z = rot.z,rot.y
        rot = rot.to_euler()
        pos = Vector((SHAR.read_float(Offset + 0x30), SHAR.read_float(Offset + 0x34), SHAR.read_float(Offset + 0x38)))
        pos.y,pos.z = pos.z,pos.y
        return pos,rot


    if GameState in ['NormalInGame', 'NormalPaused']:
        CharManager = CharacterManager()
        SMIO_info["Character"] = CharacterName(CharManager, 0)
        Player = Characters(CharManager, 0)
        InCar = CharacterInCar(Player)
        SMIO_info['Player In Car'] = InCar
        SMIO_info['Player_Position'] = CharacterPosition(Player)
        SMIO_info['Player_Rotation'] = round(CharacterRotation(Player), 2)
        if InCar:
            PlayerCar = CharacterCar(Player)
            SMIO_info['Car_Position'],SMIO_info['Car_Rotation'] = CarPosRot(PlayerCar)
    
    return SMIO_info
        
def Get_Address_From_Pointer(SHAR: Pymem, base, offsets):
    addr = SHAR.read_int(base)
    for offset in offsets[:-1]:
        addr = SHAR.read_int(addr+offset)
    return addr + offsets[-1]

def Player_Position_Address(SHAR : Pymem):
    PosX_offground  =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x388])
    PosY_offground  =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x38C])
    PosZ_offground  =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x390])

    PosX_onground   =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x108,0x10,0x14,0x14,0x48])
    PosY_onground   =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x108,0x10,0x14,0x14,0x4C])
    PosZ_onground   =       Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C922C,[0x108,0x10,0x14,0x14,0x50])
    return [
        (PosX_offground,PosY_offground,PosZ_offground),
        (PosX_onground,PosY_onground,PosZ_onground)]

def Car_PosRot_Address(SHAR : Pymem):
    pass

def Car_Pos_Address(SHAR : Pymem):
    CarPosX = Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C8994,[0x4A4,0x4A8,0x70,0x94])
    CarPosY = Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C8994,[0x4A4,0x4A8,0x70,0x98])
    CarPosZ = Get_Address_From_Pointer(SHAR,SHAR.base_address+0x2C8994,[0x4A4,0x4A8,0x70,0x9C])

    return (CarPosX,CarPosY,CarPosZ)

def SMIO_Teleport_To(position : Vector):
    try:
        SHAR = Pymem('Simpsons.exe')
    except:
        return

    SMIO = SMIO_read()
    if SMIO.get('GameState') in ['NormalInGame', 'NormalPaused']:
        if SMIO.get('Player In Car'):
            (CarPosX,CarPosY,CarPosZ) = Car_Pos_Address(SHAR)
            SHAR.write_float(CarPosX, position.x)
            SHAR.write_float(CarPosY, position.z)
            SHAR.write_float(CarPosZ, position.y)
        else:
            [(PosX_offground,PosY_offground,PosZ_offground),(PosX_onground,PosY_onground,PosZ_onground)] = Player_Position_Address(SHAR)
            SHAR.write_float(PosX_offground, position.x)
            SHAR.write_float(PosY_offground, position.z+1)
            SHAR.write_float(PosZ_offground, position.y)
            
            SHAR.write_float(PosX_onground, position.x)
            SHAR.write_float(PosY_onground, position.z)
            SHAR.write_float(PosZ_onground, position.y)