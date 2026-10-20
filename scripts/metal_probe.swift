// Native hardware prerequisite probe. This does not run or certify ASR.
import Foundation
import Metal

let source = """
#include <metal_stdlib>
using namespace metal;
kernel void probe(device const float *a [[buffer(0)]],
                  device float *b [[buffer(1)]], uint i [[thread_position_in_grid]]) {
    b[i] = a[i] * 2.0f + 1.0f;
}
"""
var results: [[String: Any]] = []
for device in MTLCopyAllDevices() {
    var row: [String: Any] = ["name": device.name, "registry_id": String(device.registryID),
        "low_power": device.isLowPower, "removable": device.isRemovable,
        "kernel_executed": false, "output_verified": false]
    do {
        let library = try device.makeLibrary(source: source, options: nil)
        guard let function = library.makeFunction(name: "probe"),
              let queue = device.makeCommandQueue(),
              let command = queue.makeCommandBuffer(),
              let encoder = command.makeComputeCommandEncoder() else {
            throw NSError(domain: "metal-probe", code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Cannot create Metal compute objects"])
        }
        let pipeline = try device.makeComputePipelineState(function: function)
        let values = (0..<256).map { Float($0) }
        let input = values.withUnsafeBytes {
            device.makeBuffer(bytes: $0.baseAddress!, length: $0.count, options: .storageModeShared)
        }
        guard let input = input,
              let output = device.makeBuffer(length: values.count * MemoryLayout<Float>.stride,
                  options: .storageModeShared) else {
            throw NSError(domain: "metal-probe", code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Cannot allocate Metal buffers"])
        }
        encoder.setComputePipelineState(pipeline)
        encoder.setBuffer(input, offset: 0, index: 0)
        encoder.setBuffer(output, offset: 0, index: 1)
        encoder.dispatchThreads(MTLSize(width: values.count, height: 1, depth: 1),
            threadsPerThreadgroup: MTLSize(width: min(pipeline.maxTotalThreadsPerThreadgroup, 64), height: 1, depth: 1))
        encoder.endEncoding()
        let started = Date()
        command.commit()
        command.waitUntilCompleted()
        row["elapsed_seconds"] = Date().timeIntervalSince(started)
        row["command_status"] = command.status.rawValue
        row["kernel_executed"] = command.status == .completed
        if let error = command.error { row["error"] = error.localizedDescription }
        if command.status == .completed {
            let actual = output.contents().bindMemory(to: Float.self, capacity: values.count)
            row["output_verified"] = values.indices.allSatisfy { actual[$0] == values[$0] * 2 + 1 }
            row["output_checksum"] = values.indices.reduce(Float(0)) { $0 + actual[$1] }
        }
    } catch { row["error"] = error.localizedDescription }
    results.append(row)
}
let verified = results.contains { ($0["kernel_executed"] as? Bool == true) && ($0["output_verified"] as? Bool == true) }
let result: [String: Any] = ["devices": results, "device_count": results.count,
    "metal_compute_available": verified, "asr_tested": false,
    "scope": "Native Metal compute prerequisite only; no CPU fallback or ASR acceptance"]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
