#-----------------------------------------------------------------------------
# Name:        smidi.py
# Purpose:     A very simplified modification of a MIDI File
#
# Author:      Christian Rüschoff <c_rue) at (web . de>
#
# Created:     2018/07/10
# Copyright:   (c) 2018 Christian Rüschoff
# License:     Please see License.txt for the terms under which this
#              software is distributed.
#-----------------------------------------------------------------------------

from MidiFile import *

class Chord:
  def __init__(self, keys, duration, velocity=100):
    self.keys = keys          # [int] if empty => Pause
    self.duration = duration  # float
    self.velocity = velocity  # int(0-127)
    

class SMidiTrack:
# storing a name, a list of chords and an instrument (MIDI Standard 0-127)
  def __init__(self, name="Track", instrument=0):
    self.name = name
    self.chords = list() # = [Chord]
    self.instrument = instrument # instrument = int(0-127) from MIDI Standard  
    # a negative values signalizes a percussion track sent to midi channel 9
  
  def append(self,chord):
    if isinstance(chord,list):
      self.chords += chord
    elif isinstance(chord,Chord):
      self.chords.append(chord)
    else:
      raise TypeError('unsupported operand type(s) for +=: \'SMidiTrack\' and \'' + type(chord) +'\'')

class SMidi:
# storing a list of tracks and a tempo
  def __init__(self,tracks,tempo=120):
    # tracks = [SMidiTrack]
    self.tracks = tracks
    self.tempo = tempo
    # more meta information
    
  def write(self,filename):
  # creates a midi track and writes it to a file
  # filename - type string, storing a file name
    no_tracks = len(self.tracks)+1
    midi = MIDIFile(no_tracks)
    midi.addTrackName(0, 0, "Meta")
    midi.addTempo(0,0,self.tempo)          # track, time, tempo
        
    # collect instruments
    instruments = set()
    for track in self.tracks:
      instruments.add(track.instrument)
      
    # set instruments
    instruments = list(instruments)
    instruments.sort()
    for instrument in instruments: # percussion instruments
      if instrument < 0:
        midi.addProgramChange(0,9,0,-1-instrument)  # track, channel, time, program
        instruments.pop(0)
      else:
        break
    
    for i in range(len(instruments)): # melodic instruments
      midi.addProgramChange(0,i,0,instruments[i])  # track, channel, time, program
                  
    # add tracknames
    chan = [] # chan[track index] = channel
    for i in range(len(self.tracks)):
      midi.addTrackName(i+1,0,self.tracks[i].name) # track, time, trackname          
      try:
        chan.append(instruments.index(self.tracks[i].instrument))
      except:
        chan.append(9)
    
    for i in range(len(self.tracks)):
      time = 0
      for chord in self.tracks[i].chords:
        for key in chord.keys:
          #print(i+1, chan[i], int(key), time, chord.duration, chord.velocity)
          midi.addNote(i+1, chan[i], key, time, chord.duration, chord.velocity)
        time += chord.duration      
      
    if isinstance(filename, str):
      with open(filename, 'wb') as midifile:
        midi.writeFile(midifile)
    else:
      midi.writeFile(filename)