import PhotosUI
import SwiftUI
import UIKit

struct CaptureView: View {
    @EnvironmentObject private var state: AppState
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var showingCamera = false

    private let providers = [
        ("configured", "Auto"),
        ("paddleocr", "Paddle"),
        ("google_vision", "Vision"),
        ("clova", "CLOVA")
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    cameraPanel
                    providerPicker
                    selectedPreview
                    actionButtons
                    resultPanel
                    messagePanel
                }
                .padding(20)
            }
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("영양제 촬영")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbarBackground(Color.black, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
        .sheet(isPresented: $showingCamera) {
            UIImagePickerView(sourceType: .camera) { image, data in
                state.setImage(
                    image,
                    data: data,
                    fileName: "ios-camera-label.jpg",
                    mimeType: "image/jpeg"
                )
            }
            .ignoresSafeArea()
        }
        .onChange(of: selectedPhotoItem) { _, item in
            Task { await loadPhoto(item) }
        }
    }

    private var cameraPanel: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 30, style: .continuous)
                .fill(Color(red: 0.03, green: 0.03, blue: 0.035))
                .frame(height: 360)
                .overlay(
                    RoundedRectangle(cornerRadius: 30, style: .continuous)
                        .stroke(Color.white.opacity(0.16), lineWidth: 1)
                )

            VStack(spacing: 24) {
                Image(systemName: "viewfinder")
                    .font(.system(size: 58, weight: .bold))
                    .foregroundStyle(Color.lemonYellow)
                Text("성분표와 섭취 방법이 선명하게 보이도록 촬영해주세요")
                    .font(.system(size: 18, weight: .black))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 34)
            }
        }
    }

    private var providerPicker: some View {
        Picker("OCR provider", selection: $state.ocrProvider) {
            ForEach(providers, id: \.0) { provider in
                Text(provider.1).tag(provider.0)
            }
        }
        .pickerStyle(.segmented)
        .disabled(state.isAnalyzing)
    }

    private var selectedPreview: some View {
        Group {
            if let selected = state.selectedImage {
                Image(uiImage: selected.image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 260)
                    .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                    .overlay(alignment: .topTrailing) {
                        Button {
                            state.clearImage()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.white, Color.black.opacity(0.64))
                        }
                        .padding(12)
                    }
            }
        }
    }

    private var actionButtons: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                    Label("갤러리", systemImage: "photo.on.rectangle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryActionButtonStyle())

                Button {
                    if UIImagePickerController.isSourceTypeAvailable(.camera) {
                        showingCamera = true
                    } else {
                        state.errorMessage = "시뮬레이터에는 연결된 카메라가 없어요. 갤러리 이미지로 OCR을 테스트해주세요."
                    }
                } label: {
                    Label("카메라", systemImage: "camera.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryActionButtonStyle())
            }

            Button {
                Task { await state.analyzeSelectedImage() }
            } label: {
                HStack {
                    if state.isAnalyzing {
                        ProgressView()
                            .tint(.black)
                    }
                    Text(state.isAnalyzing ? "분석 중" : "분석하기")
                        .font(.system(size: 18, weight: .black))
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(PrimaryActionButtonStyle())
            .disabled(state.selectedImage == nil || state.isAnalyzing)
        }
    }

    @ViewBuilder
    private var resultPanel: some View {
        if let preview = state.preview {
            VStack(alignment: .leading, spacing: 14) {
                Text("Preview")
                    .font(.system(size: 24, weight: .black))
                resultRow("Status", preview.status)
                resultRow("OCR", preview.pipelineMetadata.ocrProvider ?? "unknown")
                resultRow("YOLO ROI", preview.pipelineMetadata.visionRoiUsed ? "on" : "off")
                resultRow("Ollama parser", preview.pipelineMetadata.llmParserUsed ? "on" : "review")
                resultRow("Ingredients", "\(preview.ingredientCandidates.count)")
                resultRow("Sections", "\(preview.labelSections.count)")
                if let intakeText = preview.intakeMethod.text, !intakeText.isEmpty {
                    resultRow("Intake", intakeText)
                }
                if !preview.labelSections.isEmpty {
                    Divider()
                    ForEach(preview.labelSections.prefix(5)) { section in
                        Text("• \(section.sectionType) \(section.headingText ?? "")")
                            .font(.system(size: 15, weight: .semibold))
                    }
                }
                if !preview.ingredientCandidates.isEmpty {
                    Divider()
                    ForEach(preview.ingredientCandidates.prefix(6)) { ingredient in
                        Text("• \(ingredient.displayName) \(ingredient.amountText)")
                            .font(.system(size: 15, weight: .semibold))
                    }
                }
                if !preview.lowConfidenceFields.isEmpty {
                    Divider()
                    Text("Review: \(preview.lowConfidenceFields.prefix(6).joined(separator: ", "))")
                        .font(.footnote.weight(.bold))
                        .foregroundStyle(Color.orange)
                }
                if !preview.warnings.isEmpty {
                    Divider()
                    ForEach(preview.warnings.prefix(4), id: \.self) { warning in
                        Text(warning)
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Color.red)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(20)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        }
    }

    @ViewBuilder
    private var messagePanel: some View {
        if let message = state.errorMessage {
            Text(message)
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.red.opacity(0.84))
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        } else if let notice = state.notice {
            Text(notice)
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Color.ink)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.lemonYellow)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        }
    }

    private func resultRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(Color.slate)
                .frame(width: 110, alignment: .leading)
            Text(value)
                .fontWeight(.bold)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .font(.system(size: 15))
    }

    private func loadPhoto(_ item: PhotosPickerItem?) async {
        guard let item else { return }
        do {
            guard let data = try await item.loadTransferable(type: Data.self),
                  let image = UIImage(data: data) else {
                state.errorMessage = "선택한 이미지를 읽지 못했어요."
                return
            }
            state.setImage(
                image,
                data: normalizedImageData(from: image, originalData: data),
                fileName: "ios-gallery-label.jpg",
                mimeType: "image/jpeg"
            )
        } catch {
            state.errorMessage = "갤러리 이미지를 불러오지 못했어요: \(error.localizedDescription)"
        }
    }

    private func normalizedImageData(from image: UIImage, originalData: Data) -> Data {
        image.jpegData(compressionQuality: 0.92) ?? originalData
    }
}

private extension SupplementIngredientCandidate {
    var amountText: String {
        guard let amount else { return "" }
        let formatted = amount.truncatingRemainder(dividingBy: 1) == 0
            ? String(Int(amount))
            : String(format: "%.2f", amount)
        return "\(formatted)\(unit.map { " \($0)" } ?? "")"
    }
}

private struct PrimaryActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 16)
            .foregroundStyle(Color.ink)
            .background(Color.lemonYellow.opacity(configuration.isPressed ? 0.72 : 1))
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

private struct SecondaryActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 16, weight: .black))
            .padding(.vertical, 14)
            .foregroundStyle(.white)
            .background(Color.white.opacity(configuration.isPressed ? 0.12 : 0.18))
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}
