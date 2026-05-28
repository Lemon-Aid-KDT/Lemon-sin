import Foundation
import Combine
import SwiftUI
import UIKit

@MainActor
final class AppState: ObservableObject {
    @Published var selectedImage: SelectedSupplementImage?
    @Published var preview: SupplementAnalysisPreview?
    @Published var isAnalyzing = false
    @Published var notice: String?
    @Published var errorMessage: String?
    @Published var ocrProvider = "configured"

    let api: LemonAidAPI

    init(api: LemonAidAPI) {
        self.api = api
    }

    func setImage(_ image: UIImage, data: Data, fileName: String, mimeType: String) {
        selectedImage = SelectedSupplementImage(
            image: image,
            data: data,
            fileName: fileName,
            mimeType: mimeType
        )
        preview = nil
        errorMessage = nil
        notice = "영양제 라벨 이미지를 선택했어요."
    }

    func clearImage() {
        selectedImage = nil
        preview = nil
        errorMessage = nil
        notice = nil
    }

    func analyzeSelectedImage() async {
        guard let selectedImage else {
            errorMessage = "분석할 영양제 라벨 이미지를 먼저 선택해주세요."
            return
        }
        isAnalyzing = true
        errorMessage = nil
        defer { isAnalyzing = false }

        do {
            preview = try await api.analyzeSupplementImage(
                imageData: selectedImage.data,
                fileName: selectedImage.fileName,
                mimeType: selectedImage.mimeType,
                ocrProvider: ocrProvider
            )
            notice = "백엔드 OCR preview를 받았어요."
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct SelectedSupplementImage: Identifiable {
    let id = UUID()
    let image: UIImage
    let data: Data
    let fileName: String
    let mimeType: String
}
