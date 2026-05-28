import Foundation

struct LemonAidAPI {
    let baseURL: URL
    let bearerToken: String?
    let devGatewayToken: String?
    let session: URLSession

    static func fromEnvironment() -> LemonAidAPI {
        let environment = ProcessInfo.processInfo.environment
        let base = environment["LEMON_API_BASE_URL"] ?? "http://127.0.0.1:8000/api/v1"
        return LemonAidAPI(
            baseURL: URL(string: base.trimmedTrailingSlash())!,
            bearerToken: environment["LEMON_API_TOKEN"].nonEmpty,
            devGatewayToken: environment["LEMON_DEV_GATEWAY_TOKEN"].nonEmpty,
            session: .shared
        )
    }

    func analyzeSupplementImage(
        imageData: Data,
        fileName: String,
        mimeType: String,
        ocrProvider: String
    ) async throws -> SupplementAnalysisPreview {
        let url = baseURL.appendingPathComponent("supplements/analyze")
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(
            "multipart/form-data; boundary=\(boundary)",
            forHTTPHeaderField: "Content-Type"
        )
        if let bearerToken {
            request.setValue("Bearer \(bearerToken)", forHTTPHeaderField: "Authorization")
        }
        if let devGatewayToken {
            request.setValue(devGatewayToken, forHTTPHeaderField: "X-Lemon-Dev-Gateway-Token")
        }

        request.httpBody = MultipartBody(boundary: boundary)
            .addingField(name: "client_request_id", value: UUID().uuidString)
            .addingField(name: "ocr_provider", value: ocrProvider)
            .addingFile(
                fieldName: "image",
                fileName: fileName,
                mimeType: mimeType,
                data: imageData
            )
            .finalized()

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw LemonAidAPIError.invalidResponse
        }
        guard httpResponse.statusCode == 202 else {
            throw LemonAidAPIError.backend(statusCode: httpResponse.statusCode, body: data)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(SupplementAnalysisPreview.self, from: data)
    }
}

enum LemonAidAPIError: LocalizedError {
    case invalidResponse
    case backend(statusCode: Int, body: Data)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "백엔드 응답 형식을 확인할 수 없어요."
        case let .backend(statusCode, body):
            let message = String(data: body, encoding: .utf8)?.prefix(240)
            return "백엔드 요청 실패: HTTP \(statusCode) \(message ?? "")"
        }
    }
}

private struct MultipartBody {
    private let boundary: String
    private var data = Data()

    init(boundary: String) {
        self.boundary = boundary
    }

    func addingField(name: String, value: String) -> MultipartBody {
        var copy = self
        copy.data.append("--\(boundary)\r\n")
        copy.data.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
        copy.data.append("\(value)\r\n")
        return copy
    }

    func addingFile(
        fieldName: String,
        fileName: String,
        mimeType: String,
        data fileData: Data
    ) -> MultipartBody {
        var copy = self
        copy.data.append("--\(boundary)\r\n")
        copy.data.append(
            "Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(fileName)\"\r\n"
        )
        copy.data.append("Content-Type: \(mimeType)\r\n\r\n")
        copy.data.append(fileData)
        copy.data.append("\r\n")
        return copy
    }

    func finalized() -> Data {
        var copy = data
        copy.append("--\(boundary)--\r\n")
        return copy
    }
}

private extension Data {
    mutating func append(_ value: String) {
        append(Data(value.utf8))
    }
}

private extension String {
    var nonEmptyString: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    func trimmedTrailingSlash() -> String {
        hasSuffix("/") ? String(dropLast()) : self
    }
}

private extension Optional where Wrapped == String {
    var nonEmpty: String? {
        switch self {
        case let .some(value):
            return value.nonEmptyString
        case .none:
            return nil
        }
    }
}
