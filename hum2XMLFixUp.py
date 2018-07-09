from music21 import common
from music21 import exceptions21
from music21 import pitch
from music21 import interval
from music21 import stream
from music21 import converter
from music21 import metadata

import numpy as np
import os

#-------------------------------------------------------------------------------

def oneKrnToXml(fileSourcePath, fileName):
    '''
    Processes one pair of corresponding KRN and XML files,
    producing a new XML score with the original metadata (from the KRN score)
    and any necessary character swaps in both the metadata and lyrics.
    '''

    interimScore = transferMetadata(fileSourcePath, fileName)
    newScore = lyricSwap(interimScore)
    return newScore

def corpusKrnToXml(fileSourcePath, fileDestinationPath,
                    searchTerm=None, fileFormat='.krn'): # Either, to avoid both
    '''
    Batch processes a corpus of corresponding KRN and XML files;
    assumes same same folder, the same file name, different extensions (KRN vs XML).
    '''

    preparedFileList = prepFileList(fileSourcePath, searchTerm, fileFormat)
    for eachFile in preparedFileList: #[n]:
        try:
            xmlScore = oneKrnToXml(fileSourcePath, eachFile)
            comp = commasIn(xmlScore.metadata.composer)
            vanhemp = xmlScore.metadata.parentTitle
            op = xmlScore.metadata.opusNumber
            no = xmlScore.metadata.number
            tit = xmlScore.metadata.title
            xmlScore.write(fmt='musicxml',
                            fp=fileDestinationPath+comp+' - '+tit+'.xml')
                            # fp=fileDestinationPath+comp+' - '+vanhemp+', '+op+' '+no+' - '+tit+'.xml')
        except:
            print('Error in processing '+eachFile)

#-------------------------------------------------------------------------------

def characterSwaps(anyTextString):
    '''
    Swaps out humdrum ASCII text representations like 'a/'
    for the corresponding character with accents ('á').
    Removes the characers used forphrase analysis etc ({, }, |)
    Replaces the tilde ‘~’ used for literal dashes (in cases like ‘veux-tu’)
    with an en-dash at the end of the dashed-from word,
    and nothing at the start of the dashed-to word.
    '''

    characterDict = {'a/':'á', 'e/':'é', 'i/':'í', 'o/':'ó', 'u/':'ú',
                          'A/':'Á', 'E/':'É', 'I/':'Í', 'O/':'Ó', 'U/':'Ú',
                          'a\\':'à', 'e\\':'è', 'i\\':'ì', 'o\\':'ò', 'u\\':'ù', #Sic (backslash escaping python)
                          'A\\':'À', 'E\\':'È', 'I\\':'Ì', 'O\\':'Ò', 'U\\':'Ù',
                          'a^':'â', 'e^':'ê', 'i^':'î', 'o^':'ô', 'u^':'û',
                          'A^':'A', 'E^':'Ê', 'I^':'Î', 'O^':'Ô', 'U^':'U',
                          'a0':'å', #'e0':'', 'i0':'', 'o0':'', 'u0':'',
                          'a1':'ā', 'e1':'ē', 'i1':'ī', 'o1':'ō', 'u1':'ū',
                          'a2':'ä', 'e2':'ē', 'i2':'ï', 'o2':'ö', 'u2':'ü',
                          'c5':'ç','C5':'Ç',
                          'c6':'č','C6':'Č',
                     '{': '', '}': '', '|': '', '"': '', #Single characters to cut
                     '~': '–',} # Cheat solution for literal dash in written French e.g. ‘veux-tu'
# https://musiccog.ohio-state.edu/Humdrum/representations/text.rep.html

    output = anyTextString
    for key in characterDict:
        output = output.replace(key, characterDict[key])

    if output:
        if output[0] == '–':
            output = output[1:] #Cut first character of dashed-to word
    return(output)

def lyricSwap(score):
    '''
    Applied characterSwaps function to the lyrics (specifically) of an input score
    '''

    fullNotesAndRests = score.recurse().notesAndRests
    for note in fullNotesAndRests:
        if note.lyric:
            note.lyric = characterSwaps(note.lyric)
    return (score)

#-------------------------------------------------------------------------------

def prepFileList(fileSourcePath, searchTerm=None, fileFormat=None):
    '''
    Prepares a file list from a directory path and
    (optionally) filters for searchTerm and / or fileFormat such as '.xml')
    '''

    initialList = []
    finalList = []
    for file in os.listdir(fileSourcePath):
        initialList.append(file)
        if searchTerm is not None and fileFormat is not None:
            finalList = [x for x in initialList
                         if x.endswith(fileFormat)
                         and searchTerm in x]
        elif searchTerm is None and fileFormat is not None:
            finalList = [x for x in initialList
                         if x.endswith(fileFormat)]
        elif searchTerm is not None and fileFormat is None:
            finalList = [x for x in initialList
                     if searchTerm in x]
        elif searchTerm is None and fileFormat is None:
            finalList = initialList
    return finalList

#-------------------------------------------------------------------------------

def commasOut(text):
    '''
    For 'Surname, FirstName' to 'FirstName Surname' conversions
    '''

    if ',' in text:
        position = text.index(',')
        twoNames = (text[position+2:],' ', text[:position])
        newName = ''.join(twoNames)
    else:
        newName = text
    return newName

def commasIn(text):
    '''
    For 'FirstName Surname' to 'Surname, FirstName' conversions
    '''

    if ',' not in text:
        position = text.index(' ')#To do: ossia for 'van'?
        twoNames = (text[position+1:],', ', text[:position])
        newName = ''.join(twoNames)
    else:
        newName = text
    return newName

#-------------------------------------------------------------------------------

def transferMetadata(fileSourcePath, fileName):
    '''
    Taking an KRN score and initial XML conversion using humtools,
    transferMetadata returns an XML score with the original metadata (from the KRN score),
    including character swaps.
    Use either the '.krn' or the '.xml' for the fileName.
    '''

#     try:
    krnScore = converter.parse(fileSourcePath+fileName[0:-4]+'.krn')
    xmlScore = converter.parse(fileSourcePath+fileName[0:-4]+'.xml')
#     except:
#     ScoreError:
#         print('Error in converting score: '+fileName[0:-4])
#         pass

    md = krnScore.metadata.all()
    mdDict = dict(md)
    # NB: characterSwaps done here, once for all
    newMDDict = {k: characterSwaps(v) for k, v in mdDict.items()}

    #Special case of Composer (for commas)
    if newMDDict.get('composer'):
        comp = newMDDict.get('composer')
        xmlScore.metadata.composer = commasOut(comp)
    else:
        xmlScore.metadata.composer = 'no_composer_info'

    #Special case of Lyricist (for commas and contributor role)
    c = metadata.Contributor()
    c.role = 'lyricist'
    if newMDDict.get('lyricist'):
        lyr = newMDDict.get('lyricist')
        c.name = commasOut(lyr)
    else:
        c.name = 'no_lyricist_info'
    xmlScore.metadata.addContributor(c)

    #The rest. To do: generalise (see below)
    if newMDDict.get('parentTitle'):
        vanhemp = newMDDict.get('parentTitle')
        xmlScore.metadata.parentTitle = vanhemp
    else:
        xmlScore.metadata.parentTitle = 'no_parentTitle_info'

    if newMDDict.get('opusNumber'):
        op = newMDDict.get('opusNumber')
        xmlScore.metadata.opusNumber = op
    else:
        xmlScore.metadata.opusNumber = 'no_opusNumber_info'

    if newMDDict.get('number'):
        no = newMDDict.get('number')
        xmlScore.metadata.number = no
    else:
        xmlScore.metadata.number = 'no_number_info'

    if newMDDict.get('title'):
        tit = newMDDict.get('title')
        xmlScore.metadata.title = tit
        xmlScore.metadata.movementName = tit
    else:
        xmlScore.metadata.title = 'no_title_info'

#         metadataOfInterest = ('composer', 'lyricist',
#                               'parentTitle', 'opusNumber', 'number',
#                               'title', 'textOriginalLanguage')
#         for item in metadataOfInterest:
#             if newMDDict.get(item):
#                 value = newMDDict.get(item)
#                 "xmlScore.metadata.%s" %item
#                 %s = final # Fails from here
#             else:
#                 xmlScore.metadata.item = 'No_'+item+'_Info'

    return xmlScore

#------------------------------------------------------------------------------
