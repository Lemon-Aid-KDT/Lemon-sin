//
//  Lemon_AidApp.swift
//  Lemon-Aid
//
//  Created by 박준영 on 5/28/26.
//

import SwiftUI

@main
struct Lemon_AidApp: App {
    @StateObject private var appState = AppState(api: LemonAidAPI.fromEnvironment())

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
        }
    }
}
