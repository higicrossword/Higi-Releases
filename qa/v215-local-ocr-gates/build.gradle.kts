plugins {
    kotlin("jvm") version "2.1.21"
}
repositories { mavenCentral() }
kotlin { jvmToolchain(17) }
sourceSets { main { kotlin.srcDir("src") } }
tasks.register<JavaExec>("qaCheck") {
    dependsOn("classes")
    mainClass.set("com.example.hebrewcrossword.AdminLocalOcrGateDiagnosticsV215TestKt")
    classpath = sourceSets["main"].runtimeClasspath
}
