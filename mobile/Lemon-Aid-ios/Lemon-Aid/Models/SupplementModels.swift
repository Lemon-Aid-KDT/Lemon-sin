import Foundation

struct SupplementAnalysisPreview: Decodable {
    let analysisId: String
    let status: String
    let parsedProduct: SupplementParsedProduct
    let ingredientCandidates: [SupplementIngredientCandidate]
    let labelSections: [SupplementLabelSection]
    let intakeMethod: SupplementIntakeMethod
    let pipelineMetadata: SupplementPipelineMetadata
    let lowConfidenceFields: [String]
    let warnings: [String]
    let expiresAt: String
}

struct SupplementParsedProduct: Decodable {
    let productName: String?
    let manufacturer: String?
    let servingSize: String?
    let dailyServings: Double?
}

struct SupplementIngredientCandidate: Decodable, Identifiable {
    var id: String { "\(displayName)-\(amount ?? -1)-\(unit ?? "")" }
    let displayName: String
    let nutrientCode: String?
    let amount: Double?
    let unit: String?
    let confidence: Double
    let source: String
}

struct SupplementLabelSection: Decodable, Identifiable {
    let sectionId: String
    let sectionType: String
    let headingText: String?
    let textBundle: String?
    let requiresReview: Bool

    var id: String { sectionId }
}

struct SupplementIntakeMethod: Decodable {
    let text: String?
    let structured: SupplementStructuredIntakeMethod
    let confidence: Double?
    let requiresReview: Bool
}

struct SupplementStructuredIntakeMethod: Decodable {
    let frequency: String
    let timesPerDay: Double?
    let amountPerTime: Double?
    let amountUnit: String?
    let timeOfDay: [String]
    let withFood: String
}

struct SupplementPipelineMetadata: Decodable {
    let intakeCompleted: Bool
    let visionRoiUsed: Bool
    let ocrProvider: String?
    let llmParserUsed: Bool
    let rawImageStored: Bool
    let rawOcrTextStored: Bool
}
