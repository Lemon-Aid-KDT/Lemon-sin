import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

fun keystoreValue(name: String): String? = keystoreProperties.getProperty(name)?.takeIf {
    it.isNotBlank()
}

val releaseApplicationId = providers.gradleProperty("LEMON_ANDROID_APPLICATION_ID")
    .orElse("com.example.lemon_aid_mobile")
    .get()
val requiredKeystoreKeys = listOf("storeFile", "storePassword", "keyAlias", "keyPassword")
val defaultExampleMainActivityFile = file(
    "src/main/kotlin/com/example/lemon_aid_mobile/MainActivity.kt"
)

android {
    namespace = releaseApplicationId
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = releaseApplicationId
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    flavorDimensions += "environment"
    productFlavors {
        create("dev") {
            dimension = "environment"
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"
        }
        create("staging") {
            dimension = "environment"
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-staging"
        }
        create("prod") {
            dimension = "environment"
        }
    }

    signingConfigs {
        create("release") {
            val storeFileValue = keystoreValue("storeFile")
            if (storeFileValue != null) {
                storeFile = file(storeFileValue)
            }
            storePassword = keystoreValue("storePassword")
            keyAlias = keystoreValue("keyAlias")
            keyPassword = keystoreValue("keyPassword")
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

gradle.taskGraph.whenReady {
    val releaseTaskRequested = allTasks.any { task ->
        task.name.contains("Release", ignoreCase = false)
    }
    val missingKeystoreKeys = requiredKeystoreKeys.filter { key -> keystoreValue(key) == null }
    if (releaseTaskRequested && releaseApplicationId.startsWith("com.example.")) {
        throw GradleException(
            "Set -PLEMON_ANDROID_APPLICATION_ID to the reviewed reverse-domain app id before release builds."
        )
    }
    if (releaseTaskRequested && defaultExampleMainActivityFile.exists()) {
        throw GradleException(
            "Move MainActivity out of the com.example package after the reviewed Android id is finalized."
        )
    }
    if (releaseTaskRequested && missingKeystoreKeys.isNotEmpty()) {
        throw GradleException(
            "android/key.properties must define ${missingKeystoreKeys.joinToString()} before release builds."
        )
    }
}

flutter {
    source = "../.."
}
