from enum import Enum
import functools

class UserType(Enum): #We explcitly assign values, so if we want to delete a value, previous bitmasks do not become invalidated
    Surfer = 0
    Ordinary = 1
    Trendy = 2
    Corporate = 3
    Super = 4
    Banned=5

def addType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    if checkForType(mask, UserType.Corporate) or checkForType(mask, UserType.Super): #Super and Corporate Users can not become Trendy
        type=removeType(type, UserType.Trendy)
    elif checkForType(type, UserType.Corporate) or checkForType(type, UserType.Super): #If trendy users become corporate or super, they can no longer be trendy
        mask=removeType(mask, UserType.Trendy)
        
    return mask | (1<<type)

def removeType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    return mask & ~(1<<type)

def checkForType(mask,type):
    return bool(mask & (1<<type)==type)