import SwiftUI

struct RootView: View {
    @State private var showingSplash = true

    var body: some View {
        Group {
            if showingSplash {
                SplashView()
            } else {
                MainShellView()
            }
        }
        .task {
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            withAnimation(.easeOut(duration: 0.24)) {
                showingSplash = false
            }
        }
    }
}

private struct SplashView: View {
    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            VStack(spacing: 18) {
                Circle()
                    .fill(Color.lemonYellow)
                    .frame(width: 132, height: 132)
                    .overlay(
                        Text("L")
                            .font(.system(size: 68, weight: .black, design: .rounded))
                            .foregroundStyle(Color.ink)
                    )
                    .shadow(color: .lemonYellow.opacity(0.34), radius: 18, y: 10)
                Text("상큼하게 찍고, 똑똑하게 채워요")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(Color.slate)
            }
        }
    }
}

private struct MainShellView: View {
    var body: some View {
        TabView {
            HomeView()
                .tabItem { Label("홈", systemImage: "heart.fill") }
            ChatPlaceholderView()
                .tabItem { Label("챗", systemImage: "bubble.left.fill") }
            CaptureView()
                .tabItem { Label("촬영", systemImage: "plus.circle.fill") }
            ScorePlaceholderView()
                .tabItem { Label("점수", systemImage: "medal.fill") }
            SettingsView()
                .tabItem { Label("설정", systemImage: "gearshape.fill") }
        }
        .tint(.lemonYellow)
    }
}

private struct HomeView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 22) {
                VStack(alignment: .leading, spacing: 24) {
                    HStack {
                        Text("레몬·에이드")
                            .font(.system(size: 34, weight: .black))
                        Spacer()
                        Image(systemName: "calendar")
                        Image(systemName: "bell.fill")
                        Image(systemName: "person.fill")
                    }
                    HStack(spacing: 18) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("오늘의 건강 점수")
                                .font(.headline)
                            Text("78점")
                                .font(.system(size: 52, weight: .black))
                        }
                        Spacer()
                    }
                }
                .padding(.horizontal, 28)
                .padding(.top, 28)
                .padding(.bottom, 42)
                .background(Color.lemonYellow)

                VStack(spacing: 18) {
                    InfoCard(title: "오늘의 영양", value: "600 / 1500 kcal", subtitle: "OCR·추천 smoke용 native shell")
                    InfoCard(title: "촬영 테스트", value: "Paddle · CLOVA · Vision", subtitle: "아래 촬영 탭에서 실제 endpoint를 호출합니다.")
                    InfoCard(title: "분석 연결", value: "YOLO/Ollama는 backend runtime", subtitle: "Swift 앱은 fake endpoint를 만들지 않습니다.")
                }
                .padding(.horizontal, 24)
                .offset(y: -34)
            }
        }
        .background(Color.pageBackground)
    }
}

private struct InfoCard: View {
    let title: String
    let value: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.system(size: 22, weight: .black))
            Text(value)
                .font(.system(size: 26, weight: .black))
                .lineLimit(3)
                .minimumScaleFactor(0.72)
            Text(subtitle)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Color.slate)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(24)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .shadow(color: .black.opacity(0.05), radius: 18, y: 10)
    }
}

private struct ChatPlaceholderView: View {
    var body: some View {
        PlaceholderScreen(
            title: "레몬봇",
            message: "등록된 영양제와 알고리즘 preview를 연결한 뒤 설명 endpoint를 붙입니다.",
            symbol: "bubble.left.and.bubble.right.fill"
        )
    }
}

private struct ScorePlaceholderView: View {
    var body: some View {
        PlaceholderScreen(
            title: "식단 점수",
            message: "Swift native shell에서는 우선 영양제 OCR smoke를 검증합니다.",
            symbol: "chart.bar.fill"
        )
    }
}

private struct SettingsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        List {
            Section("API") {
                LabeledContent("Base URL", value: state.api.baseURL.absoluteString)
                LabeledContent("Gateway token", value: state.api.devGatewayToken == nil ? "not set" : "set")
                LabeledContent("Bearer token", value: state.api.bearerToken == nil ? "not set" : "set")
            }
            Section("주의") {
                Text("Xcode Scheme Environment Variables로 LEMON_API_BASE_URL, LEMON_API_TOKEN, LEMON_DEV_GATEWAY_TOKEN을 주입합니다. 앱 bundle에 .env를 넣지 않습니다.")
                    .font(.footnote)
            }
        }
        .navigationTitle("설정")
    }
}

private struct PlaceholderScreen: View {
    let title: String
    let message: String
    let symbol: String

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: symbol)
                .font(.system(size: 48, weight: .bold))
                .foregroundStyle(Color.lemonYellow)
            Text(title)
                .font(.system(size: 28, weight: .black))
            Text(message)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Color.slate)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.pageBackground)
    }
}

extension Color {
    static let lemonYellow = Color(red: 1.0, green: 0.79, blue: 0.0)
    static let ink = Color(red: 0.08, green: 0.11, blue: 0.16)
    static let slate = Color(red: 0.36, green: 0.41, blue: 0.49)
    static let pageBackground = Color(red: 0.95, green: 0.96, blue: 0.97)
}
