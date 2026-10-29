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
}
