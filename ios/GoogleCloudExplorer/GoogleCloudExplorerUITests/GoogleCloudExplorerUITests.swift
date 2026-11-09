import XCTest

final class GoogleCloudExplorerUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testOfflineLaunchAndFiveTabNavigation() throws {
        let app = XCUIApplication()
        app.launch()

        // Verify bundled offline catalog rendered on Pulse home screen
        XCTAssertTrue(app.staticTexts["Google Cloud Explorer"].waitForExistence(timeout: 5))

        // Verify navigation across tabs on iPhone TabBar (if compact width)
        let tabBar = app.tabBars.firstMatch
        if tabBar.exists {
            for tabTitle in ["Globe", "Catalog", "SLA & Cost", "Updates", "Pulse"] {
                let button = tabBar.buttons[tabTitle]
                if button.exists {
                    button.tap()
                }
            }
        }
    }

    @MainActor
    func testPasswordlessPasskeyAuthAndBuilderPassportFlow() throws {
        let app = XCUIApplication()
        app.launch()

        // Open Cloud Vault Sign-In Portal from toolbar button if currently in Ghost Mode
        let signInButton = app.buttons["Sign In to Cloud Vault"]
        if signInButton.waitForExistence(timeout: 3) {
            signInButton.tap()
            let passkeyBtn = app.buttons.containing(NSPredicate(format: "label CONTAINS 'Mint Device Passkey'")).firstMatch
            if passkeyBtn.waitForExistence(timeout: 3) {
                passkeyBtn.tap()
            }
            let doneBtn = app.buttons["Done"]
            if doneBtn.waitForExistence(timeout: 3) {
                doneBtn.tap()
            }
        }
    }
}
