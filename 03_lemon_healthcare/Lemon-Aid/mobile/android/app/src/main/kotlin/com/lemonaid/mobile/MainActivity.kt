package com.lemonaid.mobile

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.util.Base64
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.security.MessageDigest
import java.security.cert.X509Certificate
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory

class MainActivity : FlutterActivity() {
    private val cameraPermissionChannel = "com.lemonaid.mobile/camera_permission"
    private val certificatePinChannel = "com.lemonaid.mobile/certificate_pins"
    private val cameraPermissionRequestCode = 5107
    private var pendingCameraPermissionResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            cameraPermissionChannel
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "requestCameraPermission" -> requestCameraPermission(result)
                else -> result.notImplemented()
            }
        }
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            certificatePinChannel
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "verifyServerPins" -> verifyServerPins(call.arguments, result)
                else -> result.notImplemented()
            }
        }
    }

    private fun requestCameraPermission(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            result.success("granted")
            return
        }

        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            result.success("granted")
            return
        }

        if (pendingCameraPermissionResult != null) {
            result.error(
                "permission_request_in_progress",
                "A camera permission request is already in progress.",
                null
            )
            return
        }

        pendingCameraPermissionResult = result
        requestPermissions(
            arrayOf(Manifest.permission.CAMERA),
            cameraPermissionRequestCode
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != cameraPermissionRequestCode) {
            return
        }

        val result = pendingCameraPermissionResult ?: return
        pendingCameraPermissionResult = null
        val granted = grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        result.success(if (granted) "granted" else "denied")
    }

    private fun verifyServerPins(arguments: Any?, result: MethodChannel.Result) {
        val args = arguments as? Map<*, *>
        val host = args?.get("host") as? String
        val port = (args?.get("port") as? Number)?.toInt() ?: 443
        val pins = (args?.get("pins") as? List<*>)?.mapNotNull { it as? String } ?: emptyList()
        if (host.isNullOrBlank() || pins.isEmpty()) {
            result.error(
                "invalid_arguments",
                "Certificate pin verification requires host and pins.",
                null
            )
            return
        }

        val normalizedHost = host.trim()
        Thread {
            try {
                val normalizedPins = pins.map(::normalizePin).toSet()
                val socket = SSLSocketFactory.getDefault()
                    .createSocket(normalizedHost, port) as SSLSocket
                socket.use {
                    it.soTimeout = 10000
                    it.startHandshake()
                    val hostnameMatched = HttpsURLConnection
                        .getDefaultHostnameVerifier()
                        .verify(normalizedHost, it.session)
                    if (!hostnameMatched) {
                        runOnUiThread {
                            result.error(
                                "certificate_hostname_mismatch",
                                "The server certificate did not match the requested host.",
                                null
                            )
                        }
                        return@Thread
                    }
                    val peerPins = it.session.peerCertificates
                        .filterIsInstance<X509Certificate>()
                        .map(::certificatePin)
                    val matched = peerPins.any { pin -> normalizedPins.contains(pin) }
                    runOnUiThread {
                        if (matched) {
                            result.success(true)
                        } else {
                            result.error(
                                "certificate_pin_mismatch",
                                "The server certificate did not match the configured pins.",
                                null
                            )
                        }
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    result.error(
                        "certificate_pin_verification_failed",
                        "Certificate pin verification failed.",
                        null
                    )
                }
            }
        }.start()
    }

    private fun certificatePin(certificate: X509Certificate): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(certificate.encoded)
        return "sha256/" + Base64.encodeToString(digest, Base64.NO_WRAP)
    }

    private fun normalizePin(pin: String): String {
        val trimmed = pin.trim()
        return if (trimmed.startsWith("sha256/")) trimmed else "sha256/$trimmed"
    }
}
