# Credit goes to Lucas Cardellini for figuring out all the addresses and offsets
# Also thank to 

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
    
    SHAR = Pymem('Simpsons.exe')

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
        Offset = Character + 100
        v = Vector((SHAR.read_float(Offset), SHAR.read_float(Offset + 4), SHAR.read_float(Offset + 8)))
        v.y,v.z = v.z,v.y
        return v

    def CharacterManager():
        return SHAR.read_int(VersionSelect(7111792, 7111728, 7111728, 7111784))

    def Characters(CharacterManager, Index):
        return SHAR.read_int(CharacterManager + 192 + Index * 4)

    def CharacterRotation(Character):
        return SHAR.read_float(Character + 272)

    def CharacterInCar(Character):
        return SHAR.read_int(Character + 348) != 0

    def CharacterName(CharacterManager, Index):
        return SHAR.read_string(CharacterManager + 448 + Index * 64, 64)

    def CharacterCar(Character):
        return SHAR.read_int(Character + 348)        

    def CarPosRot(Car):
        Offset = Car + 184
        # m = [
        #     [SHAR.read_float(Offset), SHAR.read_float(Offset + 4), SHAR.read_float(Offset + 8), SHAR.read_float(Offset + 12)],
        #     [SHAR.read_float(Offset + 16), SHAR.read_float(Offset + 20), SHAR.read_float(Offset + 24), SHAR.read_float(Offset + 28)],
        #     [SHAR.read_float(Offset + 32), SHAR.read_float(Offset + 36), SHAR.read_float(Offset + 40), SHAR.read_float(Offset + 44)],
        #     [SHAR.read_float(Offset + 48), SHAR.read_float(Offset + 52), SHAR.read_float(Offset + 56), SHAR.read_float(Offset + 60)]
        #     ]
        rot = [
            [SHAR.read_float(Offset),       SHAR.read_float(Offset + 4),    SHAR.read_float(Offset + 8)],
            [SHAR.read_float(Offset + 16),  SHAR.read_float(Offset + 20),   SHAR.read_float(Offset + 24)],
            [SHAR.read_float(Offset + 32),  SHAR.read_float(Offset + 36),   SHAR.read_float(Offset + 40)],
            ]
        rot = Matrix(rot).to_quaternion()
        rot.y,rot.z = rot.z,rot.y
        rot = rot.to_euler()
        pos = Vector((SHAR.read_float(Offset + 48), SHAR.read_float(Offset + 52), SHAR.read_float(Offset + 56)))
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
        