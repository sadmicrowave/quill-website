import Foundation
import AppKit
import ScreenCaptureKit
import CoreImage
import CoreMedia
import ImageIO
import UniformTypeIdentifiers

// skgrab <windowID> <fps> <seconds> <outDir>: frames of one window as PNGs, through ScreenCaptureKit (works for windows `screencapture -v` cannot record)
final class Sink: NSObject, SCStreamOutput {
    let out: URL; var n = 0; let ctx = CIContext()
    init(_ out: URL) { self.out = out }
    func stream(_ stream: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sb.isValid, let attach = (CMSampleBufferGetSampleAttachmentsArray(sb, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]])?.first,
              let raw = attach[.status] as? Int, SCFrameStatus(rawValue: raw) == .complete, let px = CMSampleBufferGetImageBuffer(sb) else { return }
        let ci = CIImage(cvPixelBuffer: px)
        if let cg = ctx.createCGImage(ci, from: ci.extent),
           let dest = CGImageDestinationCreateWithURL(out.appendingPathComponent(String(format: "f%05d.jpg", n)) as CFURL, UTType.jpeg.identifier as CFString, 1, nil) {
            let opts = [kCGImageDestinationLossyCompressionQuality: 0.93] as CFDictionary
            CGImageDestinationAddImage(dest, cg, opts); CGImageDestinationFinalize(dest)
            let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
            if let h = try? FileHandle(forWritingTo: out.appendingPathComponent("times.txt")) { h.seekToEndOfFile(); h.write(String(format: "f%05d %.4f\n", n, t).data(using: .utf8)!); try? h.close() }
            n += 1
        }
    }
}
func findWindow(_ target: String) async throws -> SCWindow? {
    for _ in 0..<160 {                                      // wait up to 80 s for the window to be on screen
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)      // (a hidden window is waited for)
        let found = content.windows.first(where: { w in
            if let id = UInt32(target) { return w.windowID == id }
            let parts = target.split(separator: ":", maxSplits: 1).map(String.init)
            // "bundle.id:Title" matches a title that starts with Title; "bundle.id:=Title" matches it exactly
            let wanted = parts.count > 1 ? parts[1] : ""
            let title = w.title ?? ""
            return w.owningApplication?.bundleIdentifier == parts[0] && (wanted.hasPrefix("=") ? title == String(wanted.dropFirst()) : title.hasPrefix(wanted))
        })
        if found != nil { return found }
        try await Task.sleep(nanoseconds: 500_000_000)
    }
    return nil
}

/// One window, recorded from *delay* seconds for *secs* seconds. A stream stops when its window changes size, so it is restarted at the new size.
func record(target: String, dir: URL, fps: Double, delay: Double, secs: Double) async {
    do {
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        FileManager.default.createFile(atPath: dir.appendingPathComponent("times.txt").path, contents: nil)
        try await Task.sleep(nanoseconds: UInt64(delay * 1e9))
        let sink = Sink(dir)
        var end = Date.distantFuture                           // (the clock starts when the window is first found, not before)
        while Date() < end {
            guard let win = try await findWindow(target) else { print("no such window", target); break }
            if end == Date.distantFuture { end = Date().addingTimeInterval(secs) }
            let cfg = SCStreamConfiguration()
            cfg.width = Int(win.frame.width * 2); cfg.height = Int(win.frame.height * 2)
            cfg.minimumFrameInterval = CMTime(value: 1, timescale: CMTimeScale(fps))
            cfg.pixelFormat = kCVPixelFormatType_32BGRA; cfg.showsCursor = false; cfg.queueDepth = 6
            let stream = SCStream(filter: SCContentFilter(desktopIndependentWindow: win), configuration: cfg, delegate: nil)
            try stream.addStreamOutput(sink, type: .screen, sampleHandlerQueue: DispatchQueue(label: "grab-" + dir.lastPathComponent))
            try await stream.startCapture()
            var last = sink.n, quiet = 0
            while Date() < end {
                try await Task.sleep(nanoseconds: 250_000_000)
                if sink.n == last { quiet += 1 } else { quiet = 0; last = sink.n }
                if quiet >= 3 { break }                        // 0.75 s without a frame: probably resized, start again
            }
            try? await stream.stopCapture()
        }
        print(dir.lastPathComponent, "frames", sink.n)
    } catch { print("error", target, error) }
}

// skgrab <fps> <target|outDir|delay|seconds> ... : several windows in ONE process (separate processes stall each other)
let a = CommandLine.arguments
guard a.count >= 3, let fps = Double(a[1]) else { print("usage: skgrab fps target|dir|delay|secs ..."); exit(2) }
_ = NSApplication.shared
Task {
    await withTaskGroup(of: Void.self) { group in
        for spec in a[2...] {
            let p = spec.components(separatedBy: "|")
            guard p.count == 4, let d = Double(p[2]), let s = Double(p[3]) else { continue }
            group.addTask { await record(target: p[0], dir: URL(fileURLWithPath: p[1]), fps: fps, delay: d, secs: s) }
        }
    }
    exit(0)
}
RunLoop.main.run()
