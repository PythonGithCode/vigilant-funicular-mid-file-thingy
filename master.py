#!/usr/bin/env python
"""
This script uses pygame and pygame.midi to read live MIDI input from a connected device
and records the events (notes, pedal controls, etc.) with their timestamps.
When finished (by closing the window or pressing ESC), the script writes the data 
to a MIDI file ("output.mid") in MIDI format 0.
Note: This example does not use python-rtmidi or rtmidi.
"""

import pygame
import pygame.midi
import time
import struct

# --- MIDI File Writer Functions ---

def encode_var_len(n):
    """
    Encode an integer into a Variable Length Quantity (VLQ) used in MIDI files.
    Returns a list of integer byte values.
    """
    bytes_list = [n & 0x7F]
    while n > 127:
        n >>= 7
        bytes_list.insert(0, (n & 0x7F) | 0x80)
    return bytes_list

def write_midi_file(filename, events, division=96):
    """
    Write a list of MIDI events to a standard MIDI file.
    
    Parameters:
        filename: Name of the output MIDI file.
        events: List of tuples (timestamp, [status, data1, data2])
                where timestamp is in seconds relative to the start.
        division: Ticks per quarter note (MIDI resolution).
                  In our conversion, we assume 120 BPM so that:
                      ticks per second = division / (0.5) = division * 2.
    """
    # Sort events by timestamp
    events.sort(key=lambda x: x[0])
    
    # Create header chunk for Format 0 (single track)
    header = bytearray()
    header.extend(b'MThd')                        # Header chunk type
    header.extend(struct.pack(">I", 6))           # Header length always 6 bytes
    header.extend(struct.pack(">HHH", 0, 1, division))  # Format 0, one track, division
    
    # Build the track chunk in memory
    track = bytearray()
    last_time = 0.0
    
    # Conversion factor:
    # With a default tempo of 120 BPM (500,000 microseconds per beat) and division,
    # one beat (quarter note) lasts 0.5 sec so:
    # ticks per second = division / 0.5 = division * 2.
    ticks_per_second = division * 2
    
    for timestamp, data in events:
        # Compute delta time in seconds relative to the last event
        delta_time = timestamp - last_time
        last_time = timestamp
        # Convert delta time (seconds) to ticks (integer)
        ticks = int(round(delta_time * ticks_per_second))
        # Encode the delta time as a VLQ
        var_len = encode_var_len(ticks)
        track.extend(bytes(var_len))
        # Append the MIDI event data (3 bytes: status, data1, data2)
        track.extend(bytes(data))
    
    # Append the End-of-Track Meta Event: delta time 0, then FF 2F 00.
    track.extend(b'\x00\xFF\x2F\x00')
    
    # Create the track chunk with header 'MTrk'
    track_chunk = bytearray()
    track_chunk.extend(b'MTrk')
    # The track length is the size of track data in bytes
    track_chunk.extend(struct.pack(">I", len(track)))
    track_chunk.extend(track)
    
    # Write out the header and track chunk to the file.
    with open(filename, "wb") as f:
        f.write(header)
        f.write(track_chunk)
    print("MIDI file written to", filename)

# --- Main Pygame and MIDI Recording Code ---

def main():
    # Initialize pygame modules and pygame.midi
    pygame.init()
    pygame.midi.init()

    # Open the default MIDI input device.
    input_id = pygame.midi.get_default_input_id()
    if input_id == -1:
        print("No MIDI input device found!")
        pygame.midi.quit()
        pygame.quit()
        return

    midi_input = pygame.midi.Input(input_id)
    print("Recording from MIDI device id:", input_id)

    # Create a basic pygame window (required to capture quit/ESC events)
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("MIDI Recorder - Press ESC or close window to stop")
    clock = pygame.time.Clock()

    # A list to hold recorded events: each as (timestamp, [status, data1, data2])
    recorded_events = []

    # Record starting time (seconds)
    start_time = time.time()

    running = True
    while running:
        # Process pygame events so window can be closed
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Check if there are MIDI events waiting in the buffer
        if midi_input.poll():
            midi_events = midi_input.read(10)
            # Use current time for timestamping each event relative to start_time.
            current_time = time.time()
            for event_item in midi_events:
                # Each event_item is of the form ([status, data1, data2, data3], timestamp)
                # We'll ignore data3. Also, we use our current time difference.
                event_data = event_item[0][:3]  # Only the first 3 bytes matter.
                event_timestamp = current_time - start_time
                recorded_events.append((event_timestamp, event_data))
        
        # Update display background (optional)
        screen.fill((30, 30, 30))
        pygame.display.flip()
        clock.tick(60)  # Limit the loop to 60 frames per second

    # Cleanup: Close MIDI input, quit pygame.midi and pygame.
    midi_input.close()
    pygame.midi.quit()
    pygame.quit()

    # Write recorded MIDI events to a file
    if recorded_events:
        write_midi_file(make_output_filename(), recorded_events)
    else:
        print("No MIDI events were recorded.")


# Helper functions
import datetime

def make_output_filename(prefix="recording", extension=".mid"):
    """
    Generate an output file name with a timestamp to avoid overwriting.
    
    Args:
        prefix (str): The base name of the file.
        extension (str): The file extension, default is '.mid'.
        
    Returns:
        str: A unique file name with the current timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"



if __name__ == "__main__":
    main()
