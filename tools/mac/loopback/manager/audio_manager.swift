import Foundation
import CoreAudio

// USAGE:
// ./audio_manager enable "LedFx"
// ./audio_manager disable
// ./audio_manager volume get
// ./audio_manager volume set <0-100>
// ./audio_manager volume up [amount]
// ./audio_manager volume down [amount]
// ./audio_manager mute toggle
// ./audio_manager mute get
// ./audio_manager mute set <on|off>

func main() {
    let args = CommandLine.arguments
    guard args.count > 1 else { 
        print("Usage: enable [DriverName] | disable | volume <get|set|up|down> | mute <toggle|get|set>")
        exit(1) 
    }
    
    let command = args[1]
    
    switch command {
    case "enable":
        let driverName = args.count > 2 ? args[2] : "LedFx"
        enableLoopback(driverName: driverName)
        
    case "disable":
        disableLoopback()
        
    case "volume":
        guard args.count > 2 else { print("Usage: volume <get|set|up|down> [value]"); exit(1) }
        handleVolumeCommand(args: Array(args.dropFirst(2)))
        
    case "mute":
        guard args.count > 2 else { print("Usage: mute <toggle|get|set> [on|off]"); exit(1) }
        handleMuteCommand(args: Array(args.dropFirst(2)))
        
    default:
        print("Unknown command: \(command)")
        exit(1)
    }
}

func handleVolumeCommand(args: [String]) {
    guard let defaultDevice = getDefaultOutputDevice() else {
        print("Error: Could not find default output device.")
        exit(1)
    }
    
    let subcommand = args[0]
    
    switch subcommand {
    case "get":
        if let volume = getDeviceVolume(deviceID: defaultDevice) {
            print(String(format: "%.0f", volume * 100))
        } else {
            print("Error: Could not get volume")
            exit(1)
        }
        
    case "set":
        guard args.count > 1, let volume = Float(args[1]) else {
            print("Usage: volume set <0-100>")
            exit(1)
        }
        let normalizedVolume = max(0, min(100, volume)) / 100.0
        setDeviceVolume(deviceID: defaultDevice, volume: normalizedVolume)
        print("Success: Volume set to \(Int(normalizedVolume * 100))%")
        
    case "up":
        let amount = args.count > 1 ? Float(args[1]) ?? 5.0 : 5.0
        adjustVolume(deviceID: defaultDevice, delta: amount / 100.0)
        
    case "down":
        let amount = args.count > 1 ? Float(args[1]) ?? 5.0 : 5.0
        adjustVolume(deviceID: defaultDevice, delta: -(amount / 100.0))
        
    default:
        print("Unknown volume subcommand: \(subcommand)")
        exit(1)
    }
}

func handleMuteCommand(args: [String]) {
    guard let defaultDevice = getDefaultOutputDevice() else {
        print("Error: Could not find default output device.")
        exit(1)
    }
    
    let subcommand = args[0]
    
    switch subcommand {
    case "toggle":
        toggleMute(deviceID: defaultDevice)
        let isMuted = isDeviceMuted(deviceID: defaultDevice)
        print("Success: Mute \(isMuted ? "ON" : "OFF")")
        
    case "get":
        let isMuted = isDeviceMuted(deviceID: defaultDevice)
        print(isMuted ? "on" : "off")
        
    case "set":
        guard args.count > 1 else {
            print("Usage: mute set <on|off>")
            exit(1)
        }
        let muteState = args[1].lowercased() == "on"
        setDeviceMute(deviceID: defaultDevice, isMute: muteState)
        print("Success: Mute \(muteState ? "ON" : "OFF")")
        
    default:
        print("Unknown mute subcommand: \(subcommand)")
        exit(1)
    }
}

func enableLoopback(driverName: String) {
    // 1. Get Current Default Output (The Physical Speakers)
    guard let currentDefault = getDefaultOutputDevice() else {
        print("Error: Could not find default output.")
        exit(1)
    }
    
    // Safety check: Don't run if we are already the default
    let currentName = getDeviceName(deviceID: currentDefault)
    if currentName == "LedFx Audio System" {
        print("Already active.")
        exit(0)
    }
    
    // 2. Find the Loopback Driver
    guard let loopbackDevice = findDevice(byName: driverName) else {
        print("Error: '\(driverName)' driver not installed/loaded.")
        exit(1)
    }
    
    // 3. Create the Aggregate Device
    let uid = "com.ledfx.aggregate.auto"
    
    // Define the SubDevices
    // We list the Physical Speaker FIRST, then the Loopback.
    let subDevices: [[String: Any]] = [
        [kAudioSubDeviceUIDKey: getDeviceUID(deviceID: currentDefault)],
        [kAudioSubDeviceUIDKey: getDeviceUID(deviceID: loopbackDevice)]
    ]
    
    // THE FIX: "stacked" must be 1 (True) to CLONE audio to both devices.
    let desc: [String: Any] = [
        kAudioAggregateDeviceNameKey: "LedFx Audio System",
        kAudioAggregateDeviceUIDKey: uid,
        kAudioAggregateDeviceSubDeviceListKey: subDevices,
        kAudioAggregateDeviceMasterSubDeviceKey: getDeviceUID(deviceID: currentDefault), // Keep speakers as Master Clock
        "stacked": Int(1) 
    ]
    
    var aggregateDeviceID: AudioDeviceID = 0
    let err = AudioHardwareCreateAggregateDevice(desc as CFDictionary, &aggregateDeviceID)
    
    if err != noErr {
        print("Error creating aggregate: \(err)")
        exit(1)
    }
    
    // 4. Set it as the System Default Output
    setSystemOutput(deviceID: aggregateDeviceID)
    
    print("Success: Enabled Multi-Output (Stacked). AggregateID: \(aggregateDeviceID)")
}

func disableLoopback() {
    guard let aggregateID = findDevice(byUID: "com.ledfx.aggregate.auto") else {
        print("Aggregate not found, nothing to disable.")
        exit(0)
    }
    
    // Fallback to the first physical output found
    if let fallback = findFirstPhysicalOutput() {
        setSystemOutput(deviceID: fallback)
    }
    
    AudioHardwareDestroyAggregateDevice(aggregateID)
    print("Success: Disabled.")
}

// MARK: - Helper Functions

func getDefaultOutputDevice() -> AudioDeviceID? {
    var deviceID = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    let err = AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &deviceID)
    return err == noErr ? deviceID : nil
}

func setSystemOutput(deviceID: AudioDeviceID) {
    var id = deviceID
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, size, &id)
}

func findDevice(byName name: String) -> AudioDeviceID? {
    return getAllDevices().first { getDeviceName(deviceID: $0).contains(name) }
}

func findDevice(byUID uid: String) -> AudioDeviceID? {
    return getAllDevices().first { getDeviceUID(deviceID: $0) == uid }
}

func getAllDevices() -> [AudioDeviceID] {
    var size: UInt32 = 0
    var address = AudioObjectPropertyAddress(
        mSelector: 1684370979, // kAudioHardwarePropertyDevices ('dev#')
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size)
    let count = Int(size) / MemoryLayout<AudioDeviceID>.size
    var devices = [AudioDeviceID](repeating: 0, count: count)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &devices)
    return devices
}

func getDeviceName(deviceID: AudioDeviceID) -> String {
    var name: CFString = "" as CFString
    var size = UInt32(MemoryLayout<CFString>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: 1819173229, // kAudioDevicePropertyDeviceNameCFString ('lnam')
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &name)
    return name as String
}

func getDeviceUID(deviceID: AudioDeviceID) -> String {
    var uid: CFString = "" as CFString
    var size = UInt32(MemoryLayout<CFString>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: 1969841184, // kAudioDevicePropertyDeviceUID ('uid ')
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &uid)
    return uid as String
}

func findFirstPhysicalOutput() -> AudioDeviceID? {
    let devices = getAllDevices()
    for dev in devices {
        let name = getDeviceName(deviceID: dev)
        let uid = getDeviceUID(deviceID: dev)
        if name.contains("LedFx") || uid.contains("aggregate") || name.contains("Zoom") || name.contains("Teams") { continue }
        if hasOutputChannels(deviceID: dev) { return dev }
    }
    return nil
}

func hasOutputChannels(deviceID: AudioDeviceID) -> Bool {
    var size: UInt32 = 0
    var address = AudioObjectPropertyAddress(
        mSelector: 1937009955, // kAudioDevicePropertyStreamConfiguration ('sccf')
        mScope: 1869968496, // kAudioDevicePropertyScopeOutput ('out ')
        mElement: 0
    )
    AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &size)
    let bufferList = UnsafeMutablePointer<AudioBufferList>.allocate(capacity: Int(size))
    AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, bufferList)
    let count = bufferList.pointee.mNumberBuffers
    bufferList.deallocate()
    return count > 0
}

// MARK: - Volume Control Functions

func getDeviceVolume(deviceID: AudioDeviceID) -> Float? {
    // Check if it's an aggregate device
    if isAggregateDevice(deviceID: deviceID) {
        // Get sub-devices and return the max volume
        let subDevices = getAggregateDeviceSubDevices(deviceID: deviceID)
        var maxVolume: Float = 0.0
        
        for subDevice in subDevices {
            if hasOutputChannels(deviceID: subDevice) {
                if let volume = getScalarVolume(deviceID: subDevice) {
                    maxVolume = max(maxVolume, volume)
                }
            }
        }
        return maxVolume > 0 ? maxVolume : nil
    } else {
        return getScalarVolume(deviceID: deviceID)
    }
}

func getScalarVolume(deviceID: AudioDeviceID) -> Float? {
    var volume: Float32 = 0.0
    var size = UInt32(MemoryLayout<Float32>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyVolumeScalar,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain
    )
    
    let err = AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &volume)
    return err == noErr ? volume : nil
}

func setDeviceVolume(deviceID: AudioDeviceID, volume: Float) {
    // Check if it's an aggregate device
    if isAggregateDevice(deviceID: deviceID) {
        // Set volume on all sub-devices
        let subDevices = getAggregateDeviceSubDevices(deviceID: deviceID)
        
        for subDevice in subDevices {
            if hasOutputChannels(deviceID: subDevice) {
                setScalarVolume(deviceID: subDevice, volume: volume)
            }
        }
    } else {
        setScalarVolume(deviceID: deviceID, volume: volume)
    }
}

func setScalarVolume(deviceID: AudioDeviceID, volume: Float) {
    var vol = volume
    var size = UInt32(MemoryLayout<Float32>.size)
    
    // Set volume on master channel (element 0)
    var masterAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyVolumeScalar,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: 0
    )
    AudioObjectGetPropertyDataSize(deviceID, &masterAddress, 0, nil, &size)
    AudioObjectSetPropertyData(deviceID, &masterAddress, 0, nil, size, &vol)
    
    // Set volume on left channel (element 1)
    var leftAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyVolumeScalar,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: 1
    )
    AudioObjectGetPropertyDataSize(deviceID, &leftAddress, 0, nil, &size)
    AudioObjectSetPropertyData(deviceID, &leftAddress, 0, nil, size, &vol)
    
    // Set volume on right channel (element 2)
    var rightAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyVolumeScalar,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: 2
    )
    AudioObjectGetPropertyDataSize(deviceID, &rightAddress, 0, nil, &size)
    AudioObjectSetPropertyData(deviceID, &rightAddress, 0, nil, size, &vol)
}

func adjustVolume(deviceID: AudioDeviceID, delta: Float) {
    guard let currentVolume = getDeviceVolume(deviceID: deviceID) else {
        print("Error: Could not get current volume")
        exit(1)
    }
    
    let newVolume = max(0.0, min(1.0, currentVolume + delta))
    setDeviceVolume(deviceID: deviceID, volume: newVolume)
    print("Success: Volume set to \(Int(newVolume * 100))%")
}

// MARK: - Mute Control Functions

func isDeviceMuted(deviceID: AudioDeviceID) -> Bool {
    // Check if it's an aggregate device
    if isAggregateDevice(deviceID: deviceID) {
        // Check if any sub-device is muted
        let subDevices = getAggregateDeviceSubDevices(deviceID: deviceID)
        
        for subDevice in subDevices {
            if hasOutputChannels(deviceID: subDevice) {
                if isScalarMuted(deviceID: subDevice) {
                    return true
                }
            }
        }
        return false
    } else {
        return isScalarMuted(deviceID: deviceID)
    }
}

func isScalarMuted(deviceID: AudioDeviceID) -> Bool {
    var muted: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyMute,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain
    )
    
    let err = AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &muted)
    return err == noErr && muted == 1
}

func setDeviceMute(deviceID: AudioDeviceID, isMute: Bool) {
    // Check if it's an aggregate device
    if isAggregateDevice(deviceID: deviceID) {
        // Set mute on all sub-devices
        let subDevices = getAggregateDeviceSubDevices(deviceID: deviceID)
        
        for subDevice in subDevices {
            if hasOutputChannels(deviceID: subDevice) {
                if isMute {
                    // Store current volume before muting
                    if let currentVolume = getScalarVolume(deviceID: subDevice) {
                        storeVolume(deviceID: subDevice, volume: currentVolume)
                    }
                    setScalarVolume(deviceID: subDevice, volume: 0.0)
                } else {
                    // Restore previous volume
                    if let storedVolume = retrieveVolume(deviceID: subDevice) {
                        setScalarVolume(deviceID: subDevice, volume: storedVolume)
                    }
                }
                // Set the mute flag (some devices support it, some don't)
                setScalarMute(deviceID: subDevice, isMute: isMute)
            }
        }
    } else {
        if isMute {
            if let currentVolume = getScalarVolume(deviceID: deviceID) {
                storeVolume(deviceID: deviceID, volume: currentVolume)
            }
            setScalarVolume(deviceID: deviceID, volume: 0.0)
        } else {
            if let storedVolume = retrieveVolume(deviceID: deviceID) {
                setScalarVolume(deviceID: deviceID, volume: storedVolume)
            }
        }
        setScalarMute(deviceID: deviceID, isMute: isMute)
    }
}

// MARK: - Volume Storage Functions

func storeVolume(deviceID: AudioDeviceID, volume: Float) {
    let tempDir = FileManager.default.temporaryDirectory
    let volumeFile = tempDir.appendingPathComponent("audio_manager_volume_\(deviceID).txt")
    try? String(volume).write(to: volumeFile, atomically: true, encoding: .utf8)
}

func retrieveVolume(deviceID: AudioDeviceID) -> Float? {
    let tempDir = FileManager.default.temporaryDirectory
    let volumeFile = tempDir.appendingPathComponent("audio_manager_volume_\(deviceID).txt")
    if let volumeString = try? String(contentsOf: volumeFile, encoding: .utf8),
       let volume = Float(volumeString.trimmingCharacters(in: .whitespacesAndNewlines)) {
        // Clean up the temp file after reading
        try? FileManager.default.removeItem(at: volumeFile)
        return volume
    }
    return nil
}

func setScalarMute(deviceID: AudioDeviceID, isMute: Bool) {
    var muted: UInt32 = isMute ? 1 : 0
    let size = UInt32(MemoryLayout<UInt32>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyMute,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain
    )
    
    AudioObjectSetPropertyData(deviceID, &address, 0, nil, size, &muted)
}

func toggleMute(deviceID: AudioDeviceID) {
    let currentlyMuted = isDeviceMuted(deviceID: deviceID)
    setDeviceMute(deviceID: deviceID, isMute: !currentlyMuted)
}

// MARK: - Aggregate Device Functions

func isAggregateDevice(deviceID: AudioDeviceID) -> Bool {
    var transportType: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyTransportType,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    
    let err = AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &transportType)
    return err == noErr && transportType == kAudioDeviceTransportTypeAggregate
}

func getAggregateDeviceSubDevices(deviceID: AudioDeviceID) -> [AudioDeviceID] {
    var size: UInt32 = 0
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioAggregateDevicePropertyActiveSubDeviceList,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    
    AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &size)
    let count = Int(size) / MemoryLayout<AudioDeviceID>.size
    var subDevices = [AudioDeviceID](repeating: 0, count: count)
    AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &subDevices)
    
    return subDevices
}

main()