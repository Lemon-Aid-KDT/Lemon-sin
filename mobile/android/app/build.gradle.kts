plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.lemonaid.lemon_aid"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        // flutter_local_notifications가 요구하는 core library desugaring
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "com.lemonaid.lemon_aid"
        // health 패키지가 minSdk 26 (Android 8.0) 요구
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        multiDexEnabled = true

        // ─── 카카오 OAuth 딥링크 ───
        // AndroidManifest.xml 의 ${KAKAO_NATIVE_APP_KEY} 자리에 주입.
        // 보안: 키는 소스에 박지 않음. 빌드 시 -P 플래그 또는 환경변수로 전달:
        //   flutter build apk --dart-define=KAKAO_NATIVE_APP_KEY=xxxx \
        //                     -Pkakao.nativeAppKey=xxxx
        //   또는 ~/.gradle/gradle.properties 에 kakao.nativeAppKey=xxxx
        //
        // 미주입 상태에선 placeholder "DISABLED" 가 들어가 카카오 딥링크가 안 잡힘
        // (앱은 정상 빌드되고 카카오 버튼만 비활성).
        val kakaoNativeAppKey: String =
            (project.findProperty("kakao.nativeAppKey") as String?)
                ?: System.getenv("KAKAO_NATIVE_APP_KEY")
                ?: "DISABLED"
        manifestPlaceholders["KAKAO_NATIVE_APP_KEY"] = kakaoNativeAppKey
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    // core library desugaring (flutter_local_notifications 요구)
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}

flutter {
    source = "../.."
}
