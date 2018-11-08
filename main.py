#-----------------------------------------------------------------------------
# Name:        music.py
# Purpose:     Algorithmic music generation, outputs a MIDI file
#
# Author:      Christian Rüschoff <c_rue) at (web . de>
#
# Created:     2018/07/10
# Copyright:   (c) 2018 Christian Rüschoff
# License:     Please see License.txt for the terms under which this
#              software is distributed.
#-----------------------------------------------------------------------------

from random import *
from smidi import *

class Bunch(object):
# abstract struct type built upon a dictionary
  def __init__(self, **keywords):
    self.__dict__.update(keywords)
    
  def __str__(self):
    return str(self.__dict__)
    
    
def v2(x):
# computes 2-valuation of integer x
  if x == 0:
    return -1 # return -1 instead of infinity
  else:
    for i in range(32):
      if (x & (1 << i)):
        return i
    
    
def vp(p,x):
# computes p-valuation of integer x
  if x == 0:
    return -1 # return -1 instead of infinity
  else:
    for i in range(32):
      x, mod = divmod(x,p)
      if mod:
        return i
        
def v3(x):
  return vp(3,x)
    
    
def v(ramification,x):
# computes ramif.-valuation of integer x, generalizes the function vp
# ramification - type [int]
  l = len(ramification)-1
  if x == 0:
    return l+2
  else:
    for i in range(l):
      x, mod = divmod(x,ramification[l-i])
      if mod:
        return i
    return l+1
    
  
def Scale(str_scale,shift=0):
# returns a scale, that is an increasing list [int] in the range 0 to 12,
#               always beginning with 0 and should be made ending with 12
# str_scale - type string, sequence of numerals, each specifying the shift to the next key
#             on the diatonic scale.
# e.g. Scale("2212221") = [0,2,4,5,7,9,11,12] the major scale
  keys = [0]
  for i in range(len(str_scale)):
    keys.append(keys[-1] + int(str_scale[i % len(str_scale)]))
  return keys
  
  
class PerPitches:
# stores a periodic list of increasing midi pitches (0 to 127)
# self.scale - type [int], an increasing list of midi pitches (0 to 127)
# self.period - type (positive) integer (typically =12) the period length by which the pitches are repeated
  def __init__(self,scale,period):
    self.scale = scale
    self.period = period
    
  def __getitem__(self,rng):
  # returns a non periodic list of pitches [int] lying in the range 'rng'
  # rng - type integer or slice
    if not isinstance(rng,slice):
      rng = slice(rng,rng)
  
    pitches = []      
    low, start = divmod(rng.start,self.period)
    for pitch in self.scale:
      if pitch >= start:
        pitches.append(low*self.period + pitch)
          
    up, end = divmod(rng.stop,self.period)
    for i in range(low+1,up):
      for pitch in self.scale:
        pitches.append(i*self.period + pitch)
    
    for pitch in self.scale:
      if pitch < end:
          pitches.append(up*self.period + pitch)
      else:
          break
          
    return pitches
    
  def __str__(self): # for printing
    return str(self.scale) + str(self.period)
  
    
class Harmony:
# stores a periodic weight map for midi pitches
# self.scale - type [Bunch(pitch=?,weight=?)], where pitch is a midi key (i.e. integer from 0 to 127),
#                                                     and weight is a non-negative integer
# self.period - type (positive) integer (typically =12) the period length by which the weighted pitches are repeated

  def __init__(self,septatonic,base,p=2):
  # creates a periodic weight map using a septatonc scale starting at a base pitch
  # septatonic - type [int] of length 8, the list of pitches
  # base - type int, the base pitch shift by which the pitches are transposed
  # e.g. Harmony(Scale("2212221"),b).scale stores the 12 keys b to b+11 with weights [5,1,2,1,3,2,1,4,1,2,1,3]
    keys = [1]*12
    for k in range(0,7):
      keys[septatonic[(base+k)%7]] = 2+vp(2,8+k)
      
    self.scale = []
    for k in range(0,12):
      self.scale.append(Bunch(pitch = k, weight = keys[k]))
    self.period = 12
    
    
  def __getitem__(self, weight):
  # returns the periodic list of pitches (type PerPitches) lying in the weight range 'weight'
  # weight - type slice, the range of weights taken into account
    if not isinstance(weight,slice):
      weight = slice(weight,weight)
        
    crop_scale = []
    for k in self.scale:
      if (weight.start is None) or weight.start <= k.weight:
        if (weight.stop is None) or k.weight <= weight.stop:
          crop_scale.append(k.pitch)
    
    return PerPitches(crop_scale, self.period)
    
  
  def __str__(self): # for printing
    s = ''
    for k in self.scale:
      s += str(k)
    return s
      

class Metrum:
# stores a weighted list of times
# self.beats - type Bunch(time, weight), with 'time' of type float and 'weight' of type int

  def __init__(self,ramification):
  # creates a meter using a ramification 
  # e.g. Metrum([4,2]).beats has times [0, .5, 1, 1.5, 2, 2.5, 3, 3.5, 4] with weights []
    no_beats = 1
    for r in ramification:
      no_beats *= r
    
    self.beats = []
    for i in range(no_beats+1):
      self.beats.append(Bunch(time=i*ramification[0]/no_beats,weight=v(ramification,i)))
          
  def __getitem__(self, weight):
  # returns the list of times [float] lying in the range 'weight'
  # weight - type slice, the range of weights taken into account
    if not isinstance(weight,slice):
      weight = slice(weight,weight)
        
    beats = []
    for beat in self.beats:
      if weight.start is None or weight.start <= beat.weight:
        if weight.stop is None or beat.weight <= weight.stop:
          beats.append(beat.time)
    return beats
    
  def __str__(self): # for printing
    s = ''
    for beat in self.beats:
      s += str(beat) + '\n'
    return s
    
    
# Three callable classes used as input for the function 'Motive':
    
class Lin:  # returns value+step*num_call
  def __init__(self,value=0, step=0):
    self.value = value-step
    self.step = step
    
  def __call__(self):
    self.value += self.step
    return self.value
    
class Rnd:  # returns randint(low,up), first call seeds
  def __init__(self,low,up=None,step=1,seed=None):
    self.low = low
    self.up = up
    if not up is None:
      if up < low:
        self.low = low
        self.up = up
    self.step = step
    self.rnd = Random(seed)
    
  def __call__(self):
    return self.rnd.randrange(self.low,self.up,self.step)

class Walk: # returns values of a random walk in range low-up, by step size, first call seeds
  def __init__(self,value,low,up=None,step=1,seed=None):
    self.value = value
    self.low = low
    self.up = up
    if not up is None:
      if up < low:
        self.low = low
        self.up = up
    self.step = step
    self.rnd = Random(seed)
    
  def __call__(self):
    self.value += (self.rnd.randint(0,1)*2-1)*self.step
    if not self.up is None:
      self.value = min(self.value,self.up)
    self.value = max(self.value,self.low-1)      
    return self.value


def Motive(hits, metrum, beat, duration, velocity, harmony, melodies):
# generates and returns a list of chords [Chord]
# hits - the number of key/chord hits that should be played
# metrum - type Metrum, all hits ly on this metrum
# beat, duration, velocity - callable classes returning integers, specifying the
#                            position/duration within the metrum, a hit's velocity
# harmony - type Harmony, all keys ly in this harmony
# melodies - type, a list of callable classes returning integers,
#            specifying the key within the harmony

  times = list()
  for i in range(hits+1):
    times.append( beat() )
  
  times.sort()    
  max_dur = 2*(times[-1] - times[0])//len(times)
  
  for i in range(len(times)):
    times[i] %= len(metrum)-1  
  
  times = list(set(times))
  times.sort()
  
  chords = []
  if metrum[times[0]]:
    chords.append(Chord(list(), metrum[times[0]]))
    
  for i in range(len(times)-1):
    keys = []
    for melody in melodies:
      keys.append(harmony[melody() % len(harmony)])
    dur = max((duration()*(times[i+1] - times[i])) // 100,1)
    dur = min(dur,max_dur)
    dur = metrum[times[i] + dur] - metrum[times[i]]
    chords.append(Chord(keys, dur, velocity = velocity() ))
    if dur < (metrum[times[i+1]] - metrum[times[i]]):
      chords.append(Chord(list(), (metrum[times[i+1]] - metrum[times[i]])-dur))
    
  if metrum[times[len(times)-1]] < metrum[-1]:
    chords.append(Chord(list(), metrum[-1] - metrum[times[len(times)-1]] ) )
    
  return chords
  
  
def main(argv):
  tracks = []
  harmony = []
  metrum = []

  track_len = 81

  #seed(1)
  shift = randint(0,8)
  major = Scale("2212221",shift)
  arab =  Scale("1312131",shift)
  hmoll = Scale("2122131",shift)  
  
  # building meter and harmony
  bars = 0
  for i in range(track_len):
    harmony.append(Harmony(hmoll, randint(0,7)+3*v2(1+i)))
    mlen = 1+2*3**v3(1+i)
    print(mlen)
    metrum.append(Metrum([mlen,1,2,2,6]))
    bars += mlen
    
  print(bars)
    
  drumkit = -26 # negative values for percussion tracks
  
  track = SMidiTrack("Bassdrum1", drumkit)
  for i in range(track_len):
    track.append(Motive(1+2**(1+v3(1+i)),metrum[i][1:], Lin(40,5+3*v2(1+i)), Lin(0), Rnd(80,110), [35], [Lin(0)] ))
  tracks.append(track)  

  track = SMidiTrack("Bassdrum2", drumkit)
  for i in range(track_len):
    track.append(Motive(1+2*v3(1+i),metrum[i][3:], Lin(0,5+3*v2(1+i)), Lin(0), Rnd(80,120), [36], [Lin(0)] )) #Rnd(60,100,1,2+v2(1+i))
  tracks.append(track)  

  track = SMidiTrack("Snare", drumkit)
  for i in range(track_len):
    track.append(Motive(4+2**(2+v3(1+i)),metrum[i][1:], Lin(210,4-v3(1+i)), Lin(0), Rnd(70,90), [38], [Lin(0)] ))
  tracks.append(track)  

  track = SMidiTrack("Clap", drumkit)
  for i in range(track_len):
    track.append(Motive(2**(1+v3(1+i)),metrum[i][1:], Lin(40,6+v2(1+i)), Lin(0), Rnd(60,80), [39], [Lin(0)] ))
  tracks.append(track)  

  track = SMidiTrack("Tomtoms", drumkit)
  for i in range(track_len):
    track.append(Motive(2+2*v2(1+i),metrum[i][1:], Rnd(30,100,4-v2(1+i)//2,1+v2(1+i)), Lin(0), Rnd(20,60), [41,43,45,47,48,50], [Lin(v2(1+i),1+v2(1+i))] ))
  tracks.append(track)  

  track = SMidiTrack("Crash", drumkit)
  for i in range(track_len):
    track.append(Motive(1+v3(1+i)//2,metrum[i][4:], Lin(27,13), Lin(0), Lin(50), [49], [Lin(0)] ))
  tracks.append(track)  

  track = SMidiTrack("Hihat (closed)", drumkit)
  for i in range(track_len):
    track.append(Motive(2**(2+v3(1+i)),metrum[i][0:], Lin(200,6-v3(1+i)), Lin(0), Lin(50), [42], [Rnd(0,2)] ))
  tracks.append(track)  

  track = SMidiTrack("Hihat (open)", drumkit)
  for i in range(track_len):
    track.append(Motive(2*(2+v3(1+i)),metrum[i][2:], Rnd(50,300,8-v2(1+i)), Lin(0), Lin(50), [46], [Rnd(0,2)] ))
  tracks.append(track)  

  
  track = SMidiTrack("Bass", 35)
  for i in range(track_len):
    track.append(Motive(4+2*v3(1+i),metrum[i][2:], Rnd(0,300,1,1+v2(1+i)), Rnd(0,50), Lin(100), harmony[i][4:][24:36], [Lin(0)] ))
  tracks.append(track)

  #track = SMidiTrack("Bass 2", 38)
  #for i in range(track_len):
  #  track.append(Motive(4+2*v3(1+i),metrum[i][2:], Lin(49,7), Rnd(50,100), Lin(90), harmony[i][4:][24:36], [Lin(0,1)]))
  #tracks.append(track)
  
  track = SMidiTrack("Synth Arpeggio", 38)
  for i in range(track_len):
    track.append(Motive(8+4*v2(1+i),metrum[i][1:], Lin(220,7), Lin(0), Lin(50), harmony[i][3:][44:60], [Lin(0,3)]))
  tracks.append(track)

  
  track = SMidiTrack("Marimba", 12)
  for i in range(track_len):
    track.append(Motive(16+2*v2(1+i),metrum[i][2:], Rnd(100,300), Rnd(40,60), Rnd(20,60), harmony[i][2:][50:64], [Walk(7,0,14,2+v2(1+i)), Walk(5,0,14,2+v2(1+i))]))
  tracks.append(track)
  
  track = SMidiTrack("Guitar", 26)
  for i in range(track_len):
    track.append(Motive(4+4*v2(1+i),metrum[i][1:], Lin(34,13), Rnd(50,100), Lin(40), harmony[i][3:][56:72], [Walk(randint(1,3),0,4,1+i%2,2+v2(1+i))]))
  tracks.append(track)
  
  track = SMidiTrack("Sax", 65)
  for i in range(track_len):
    track.append(Motive(12,metrum[i][1:], Rnd(80,120), Rnd(40,60), Rnd(70,80), harmony[i][2:][48:84], [Walk(randint(4,17),0,21,1,3+v2(1+i))]))
  tracks.append(track)

  track = SMidiTrack("Flute", 73)
  for i in range(track_len):
    track.append(Motive(12,metrum[i][1:], Rnd(160,200), Rnd(60,80), Rnd(40,50), harmony[i][2:][76:100], [Walk(randint(4,10),0,13,1+i%2,2+v2(1+i))]))
  tracks.append(track)

  #track = SMidiTrack("Strings", 51)
  #for i in range(track_len):
  #  track.append(Motive(1,metrum[i][3:], Lin(0,300), Rnd(80,100), Lin(50), harmony[i][2:][68:104], [Lin(0),Lin(2),Lin(3),Lin(4)]))
  #tracks.append(track)
  
  track = SMidiTrack("Pad", 89)
  for i in range(track_len):
    track.append(Motive(1,metrum[i][3:], Lin(0,300), Rnd(80,100), Lin(20), harmony[i][4:][56:104], [Lin(0),Lin(1),Lin(2),Lin(3)]))
  tracks.append(track)


  smidi = SMidi(tracks,120)
  smidi.write("demo.mid")
  
  
if __name__ == "__main__":
  main(sys.argv[1:])