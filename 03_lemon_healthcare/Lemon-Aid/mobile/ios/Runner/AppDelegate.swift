import AVFoundation
import CryptoKit
import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  private let cameraPermissionChannel = "com.lemonaid.mobile/camera_permission"
  private let certificatePinChannel = "com.lemonaid.mobile/certificate_pins"
  private var certificatePinVerifiers: [CertificatePinVerificationDelegate] = []

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    let permissionChannel = FlutterMethodChannel(
      name: cameraPermissionChannel,
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    permissionChannel.setMethodCallHandler { [weak self] call, result in
      switch call.method {
      case "requestCameraPermission":
        self?.requestCameraPermission(result)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
    let pinChannel = FlutterMethodChannel(
      name: certificatePinChannel,
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    pinChannel.setMethodCallHandler { [weak self] call, result in
      switch call.method {
      case "verifyServerPins":
        self?.verifyServerPins(call, result)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private func requestCameraPermission(_ result: @escaping FlutterResult) {
    switch AVCaptureDevice.authorizationStatus(for: .video) {
    case .authorized:
      result("granted")
    case .notDetermined:
      AVCaptureDevice.requestAccess(for: .video) { granted in
        DispatchQueue.main.async {
          result(granted ? "granted" : "denied")
        }
      }
    case .denied:
      result("denied")
    case .restricted:
      result("restricted")
    @unknown default:
      result("denied")
    }
  }

  private func verifyServerPins(_ call: FlutterMethodCall, _ result: @escaping FlutterResult) {
    guard
      let arguments = call.arguments as? [String: Any],
      let host = arguments["host"] as? String,
      !host.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
      let pins = arguments["pins"] as? [String],
      !pins.isEmpty
    else {
      result(
        FlutterError(
          code: "invalid_arguments",
          message: "Certificate pin verification requires host and pins.",
          details: nil
        )
      )
      return
    }

    let normalizedHost = host.trimmingCharacters(in: .whitespacesAndNewlines)
    let port = arguments["port"] as? Int ?? 443
    let verifier = CertificatePinVerificationDelegate(host: normalizedHost, port: port, pins: pins) {
      [weak self] verifier, outcome in
      DispatchQueue.main.async {
        self?.certificatePinVerifiers.removeAll { $0 === verifier }
        switch outcome {
        case .matched:
          result(true)
        case .mismatched:
          result(
            FlutterError(
              code: "certificate_pin_mismatch",
              message: "The server certificate did not match the configured pins.",
              details: nil
            )
          )
        case .failed:
          result(
            FlutterError(
              code: "certificate_pin_verification_failed",
              message: "Certificate pin verification failed.",
              details: nil
            )
          )
        case .trustFailed:
          result(
            FlutterError(
              code: "certificate_trust_evaluation_failed",
              message: "The server certificate failed trust or hostname evaluation.",
              details: nil
            )
          )
        }
      }
    }
    certificatePinVerifiers.append(verifier)
    verifier.start()
  }
}

private enum CertificatePinVerificationOutcome {
  case matched
  case mismatched
  case failed
  case trustFailed
}

private final class CertificatePinVerificationDelegate: NSObject, URLSessionDelegate {
  init(
    host: String,
    port: Int,
    pins: [String],
    completion: @escaping (CertificatePinVerificationDelegate, CertificatePinVerificationOutcome) ->
      Void
  ) {
    self.host = host
    self.port = port
    self.pins = Set(pins.map(Self.normalizePin))
    self.completion = completion
  }

  private let host: String
  private let port: Int
  private let pins: Set<String>
  private let completion: (CertificatePinVerificationDelegate, CertificatePinVerificationOutcome) ->
    Void
  private var session: URLSession?
  private var completed = false

  func start() {
    var components = URLComponents()
    components.scheme = "https"
    components.host = host
    if port != 443 {
      components.port = port
    }
    components.path = "/"
    guard let url = components.url else {
      finish(.failed)
      return
    }
    let session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: nil)
    self.session = session
    session.dataTask(with: url) { [weak self] _, _, error in
      guard let self else { return }
      if error != nil && !completed {
        finish(.failed)
      }
    }.resume()
  }

  func urlSession(
    _ session: URLSession,
    didReceive challenge: URLAuthenticationChallenge,
    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
  ) {
    guard
      challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
      let trust = challenge.protectionSpace.serverTrust
    else {
      completionHandler(.performDefaultHandling, nil)
      return
    }

    let sslPolicy = SecPolicyCreateSSL(true, host as CFString)
    SecTrustSetPolicies(trust, sslPolicy)

    var trustError: CFError?
    guard SecTrustEvaluateWithError(trust, &trustError) else {
      completionHandler(.cancelAuthenticationChallenge, nil)
      finish(.trustFailed)
      return
    }

    for index in 0..<SecTrustGetCertificateCount(trust) {
      guard let certificate = SecTrustGetCertificateAtIndex(trust, index) else {
        continue
      }
      let certificateData = SecCertificateCopyData(certificate) as Data
      if pins.contains(Self.pin(for: certificateData)) {
        completionHandler(.useCredential, URLCredential(trust: trust))
        finish(.matched)
        return
      }
    }

    completionHandler(.cancelAuthenticationChallenge, nil)
    finish(.mismatched)
  }

  private func finish(_ outcome: CertificatePinVerificationOutcome) {
    guard !completed else { return }
    completed = true
    session?.invalidateAndCancel()
    completion(self, outcome)
  }

  private static func pin(for certificateData: Data) -> String {
    let digest = SHA256.hash(data: certificateData)
    return "sha256/" + Data(digest).base64EncodedString()
  }

  private static func normalizePin(_ pin: String) -> String {
    let trimmed = pin.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.hasPrefix("sha256/") ? trimmed : "sha256/" + trimmed
  }
}
