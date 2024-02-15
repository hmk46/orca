# Orca
#
# Copyright 2004-2009 Sun Microsystems Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., Franklin Street, Fifth Floor,
# Boston MA  02110-1301 USA.

"""Manages the default speech server for orca.  A script can use this
as its speech server, or it can feel free to create one of its own."""

__id__        = "$Id$"
__version__   = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2005-2009 Sun Microsystems Inc."
__license__   = "LGPL"

import importlib
import time

from . import debug
from . import logger
from . import settings
from . import speech_generator
from .speechserver import VoiceFamily

from .acss import ACSS

_logger = logger.getLogger()
log = _logger.newLog("speech")

# The speech server to use for all speech operations.
#
_speechserver = None

# The last time something was spoken.
_timestamp = 0

def _initSpeechServer(moduleName, speechServerInfo):

    global _speechserver

    if not moduleName:
        return

    factory = None
    try:
        factory = importlib.import_module(f'orca.{moduleName}')
    except Exception:
        try:
            factory = importlib.import_module(moduleName)
        except Exception:
            debug.printException(debug.LEVEL_SEVERE)

    # Now, get the speech server we care about.
    #
    speechServerInfo = settings.speechServerInfo
    if speechServerInfo:
        _speechserver = factory.SpeechServer.getSpeechServer(speechServerInfo)

    if not _speechserver:
        _speechserver = factory.SpeechServer.getSpeechServer()
        if speechServerInfo:
            tokens = ["SPEECH: Invalid speechServerInfo:", speechServerInfo]
            debug.printTokens(debug.LEVEL_INFO, tokens, True)

    if not _speechserver:
        raise Exception(f"ERROR: No speech server for factory: {moduleName}")

def init():
    debug.printMessage(debug.LEVEL_INFO, 'SPEECH: Initializing', True)
    if _speechserver:
        debug.printMessage(debug.LEVEL_INFO, 'SPEECH: Already initialized', True)
        return

    try:
        moduleName = settings.speechServerFactory
        _initSpeechServer(moduleName, settings.speechServerInfo)
    except Exception:
        moduleNames = settings.speechFactoryModules
        for moduleName in moduleNames:
            if moduleName != settings.speechServerFactory:
                try:
                    _initSpeechServer(moduleName, None)
                    if _speechserver:
                        break
                except Exception:
                    debug.printException(debug.LEVEL_SEVERE)

    if _speechserver:
        tokens = ["SPEECH: Using speech server factory:", moduleName]
        debug.printTokens(debug.LEVEL_INFO, tokens, True)
    else:
        msg = 'SPEECH: Not available'
        debug.printMessage(debug.LEVEL_INFO, msg, True)

    debug.printMessage(debug.LEVEL_INFO, 'SPEECH: Initialized', True)

def checkSpeechSetting():
    msg = "SPEECH: Checking speech setting."
    debug.printMessage(debug.LEVEL_INFO, msg, True)

    if not settings.enableSpeech:
        shutdown()
    else:
        init()

def __resolveACSS(acss=None):
    if isinstance(acss, ACSS):
        family = acss.get(acss.FAMILY)
        try:
            family = VoiceFamily(family)
        except Exception:
            family = VoiceFamily({})
        acss[acss.FAMILY] = family
        return acss
    elif isinstance(acss, list) and len(acss) == 1:
        return ACSS(acss[0])
    elif isinstance(acss, dict):
        return ACSS(acss)
    else:
        voices = settings.voices
        return ACSS(voices[settings.DEFAULT_VOICE])

def sayAll(utteranceIterator, progressCallback):
    if settings.silenceSpeech:
        return
    if _speechserver:
        _speechserver.sayAll(utteranceIterator, progressCallback)
    else:
        for [context, acss] in utteranceIterator:
            logLine = f"SPEECH OUTPUT: '{context.utterance}'"
            debug.printMessage(debug.LEVEL_INFO, logLine, True)
            log.info(logLine)

def _speak(text, acss, interrupt):
    """Speaks the individual string using the given ACSS."""

    if not _speechserver:
        logLine = f"SPEECH OUTPUT: '{text}' {acss}"
        debug.printMessage(debug.LEVEL_INFO, logLine, True)
        log.info(logLine)
        return

    voice = ACSS(settings.voices.get(settings.DEFAULT_VOICE))
    try:
        voice.update(__resolveACSS(acss))
    except Exception as error:
        msg = f"SPEECH: Exception updated voice with {acss}: {error}"
        debug.printMessage(debug.LEVEL_INFO, msg, True)

    resolvedVoice = __resolveACSS(voice)
    msg = f"SPEECH OUTPUT: '{text}' {resolvedVoice}"
    debug.printMessage(debug.LEVEL_INFO, msg, True)
    _speechserver.speak(text, resolvedVoice, interrupt)

def speak(content, acss=None, interrupt=True):
    """Speaks the given content.  The content can be either a simple
    string or an array of arrays of objects returned by a speech
    generator."""

    if settings.silenceSpeech:
        return

    validTypes = (str, list, speech_generator.Pause,
                  speech_generator.LineBreak, ACSS)
    error = "SPEECH: Bad content sent to speak():"
    if not isinstance(content, validTypes):
        debug.printMessage(debug.LEVEL_INFO, error + str(content), True, True)
        return

    global _timestamp
    if _timestamp:
        msg = f"SPEECH: Last spoke {time.time() - _timestamp:.4f} seconds ago"
        debug.printMessage(debug.LEVEL_INFO, msg, True)
    _timestamp = time.time()

    if isinstance(content, str):
        msg = f"SPEECH: Speak '{content}' acss: {acss}"
        debug.printMessage(debug.LEVEL_INFO, msg, True)
    else:
        tokens = ["SPEECH: Speak", content, ", acss:", acss]
        debug.printTokens(debug.LEVEL_INFO, tokens, True)

    if isinstance(content, str):
        _speak(content, acss, interrupt)
    if not isinstance(content, list):
        return

    toSpeak = []
    activeVoice = acss
    if acss is not None:
        activeVoice = ACSS(acss)

    for element in content:
        if not isinstance(element, validTypes):
            debug.printMessage(debug.LEVEL_INFO, error + str(element), True, True)
        elif isinstance(element, list):
            speak(element, acss, interrupt)
        elif isinstance(element, str):
            if len(element):
                toSpeak.append(element)
        elif toSpeak:
            newVoice = ACSS(acss)
            newItemsToSpeak = []
            if isinstance(element, speech_generator.Pause):
                if toSpeak[-1] and toSpeak[-1][-1].isalnum():
                    toSpeak[-1] += '.'
            elif isinstance(element, ACSS):
                newVoice.update(element)
                if activeVoice is None:
                    activeVoice = newVoice
                if newVoice == activeVoice:
                    continue
                tokens = ["SPEECH: New voice", newVoice, " != active voice", activeVoice]
                debug.printTokens(debug.LEVEL_INFO, tokens, True)
                newItemsToSpeak.append(toSpeak.pop())

            if toSpeak:
                string = " ".join(toSpeak)
                _speak(string, activeVoice, interrupt)
            activeVoice = newVoice
            toSpeak = newItemsToSpeak

    if toSpeak:
        string = " ".join(toSpeak)
        _speak(string, activeVoice, interrupt)

def speakKeyEvent(event, acss=None):
    """Speaks a key event immediately.

    Arguments:
    - event: input_event.KeyboardEvent to speak.
    """

    if settings.silenceSpeech:
        return

    global _timestamp
    if _timestamp:
        msg = f"SPEECH: Last spoke {time.time() - _timestamp:.4f} seconds ago"
        debug.printMessage(debug.LEVEL_INFO, msg, True)
    _timestamp = time.time()

    keyname = event.getKeyName()
    lockingStateString = event.getLockingStateString()
    acss = __resolveACSS(acss)
    msg = f"{keyname} {lockingStateString}"
    logLine = f"SPEECH OUTPUT: '{msg.strip()}' {acss}"
    debug.printMessage(debug.LEVEL_INFO, logLine, True)
    log.info(logLine)

    if _speechserver:
        _speechserver.speakKeyEvent(event, acss)

def speakCharacter(character, acss=None):
    """Speaks a single character immediately.

    Arguments:
    - character: text to be spoken
    - acss:      acss.ACSS instance; if None,
                 the default voice settings will be used.
                 Otherwise, the acss settings will be
                 used to augment/override the default
                 voice settings.
    """
    if settings.silenceSpeech:
        return

    global _timestamp
    if _timestamp:
        msg = f"SPEECH: Last spoke {time.time() - _timestamp:.4f} seconds ago"
        debug.printMessage(debug.LEVEL_INFO, msg, True)
    _timestamp = time.time()

    acss = __resolveACSS(acss)
    tokens = [f"SPEECH OUTPUT: '{character}'", acss]
    debug.printTokens(debug.LEVEL_INFO, tokens, True)
    log.info(f"SPEECH OUTPUT: '{character}'")

    if _speechserver:
        _speechserver.speakCharacter(character, acss=acss)

def getInfo():
    info = None
    if _speechserver:
        info = _speechserver.getInfo()

    return info

def stop():
    if _speechserver:
        _speechserver.stop()

def shutdown():
    debug.printMessage(debug.LEVEL_INFO, 'SPEECH: Shutting down', True)
    global _speechserver
    if _speechserver:
        _speechserver.shutdownActiveServers()
        _speechserver = None

def reset(text=None, acss=None):
    if _speechserver:
        _speechserver.reset(text, acss)

def getSpeechServer():
    return _speechserver
