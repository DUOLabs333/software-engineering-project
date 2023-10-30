import functools

SURFER=0
ORDINARY=1
TRENDY=2
CORPORATE=3
SUPER = 4
BANNED = 5

def addType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    if checkForType(mask, CORPORATE) or checkForType(mask, SUPER): #SUPER and CORPORATE Users can not become TRENDY
        type=removeType(type, TRENDY)
    elif checkForType(type, CORPORATE) or checkForType(type, SUPER): #If TRENDY users become CORPORATE or SUPER, they can no longer be TRENDY
        mask=removeType(mask, TRENDY)
        
    return mask | (1<<type)

def removeType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    return mask & ~(1<<type)

def checkForType(mask,type):
    return bool(mask & (1<<type)==type)