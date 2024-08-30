#include <hideo-base/scafold.h>
#include <karm-kira/context-menu.h>
#include <karm-kira/dialog.h>
#include <karm-kira/error-page.h>
#include <karm-kira/side-panel.h>
#include <karm-mime/mime.h>
#include <karm-sys/file.h>
#include <karm-sys/launch.h>
#include <karm-ui/drag.h>
#include <karm-ui/input.h>
#include <karm-ui/popover.h>
#include <karm-ui/scroll.h>
#include <vaev-driver/fetcher.h>
#include <vaev-view/inspect.h>
#include <vaev-view/view.h>

namespace Hideo::Browser {

enum struct SidePanel {
    CLOSE,
    DEVELOPER_TOOLS,
};

struct State {
    Mime::Url url;
    Res<Strong<Vaev::Dom::Document>> dom;
    SidePanel sidePanel = SidePanel::CLOSE;

    bool canGoBack() const {
        return false;
    }

    bool canGoForward() const {
        return false;
    }
};

struct Reload {};

struct GoBack {};

struct GoForward {};

using Action = Union<Reload, GoBack, GoForward, SidePanel>;

void reduce(State &s, Action a) {
    a.visit(Visitor{
        [&](Reload) {
            s.dom = Vaev::Driver::fetchDocument(s.url);
        },
        [&](GoBack) {
        },
        [&](GoForward) {
        },
        [&](SidePanel p) {
            s.sidePanel = p;
        },
    });
}

using Model = Ui::Model<State, Action, reduce>;

Ui::Child mainMenu([[maybe_unused]] State const &s) {
    return Kr::contextMenuContent({
        Ui::separator(),
        Kr::contextMenuItem(Ui::NOP, Mdi::PRINTER, "Print..."),
        Kr::contextMenuItem(
            [&](auto &n) {
                auto res = Sys::launch(Mime::Uti::PUBLIC_OPEN, s.url);
                if (not res)
                    Ui::showDialog(
                        n,
                        Kr::alert(
                            "Error"s,
                            Io::format("Failed to open in browser\n\n{}", res).unwrap()
                        )
                    );
            },
            Mdi::WEB, "Open in browser..."
        ),
        Ui::separator(),
        Kr::contextMenuItem(Model::bind(SidePanel::DEVELOPER_TOOLS), Mdi::CODE_TAGS, "Inspector"),
    });
}

Ui::Child addressBar(Mime::Url const &url) {
    return Ui::hflow(
               0,
               Math::Align::CENTER,
               Ui::text("{}", url),
               Ui::grow(NONE)
           ) |
           Ui::box({
               .padding = {12, 0, 0, 0},
               .borderRadii = 4,
               .borderWidth = 1,
               .backgroundFill = Ui::GRAY800,
           });
}

Ui::Child contextMenu(State const &s) {
    return Kr::contextMenuContent({
        Kr::contextMenuDock({
            Kr::contextMenuIcon(Model::bind<Reload>(), Mdi::REFRESH),
        }),
        Ui::separator(),
        Kr::contextMenuItem(
            [s](auto &) {
                (void)Sys::launch(Mime::Uti::PUBLIC_MODIFY, s.url);
            },
            Mdi::CODE_TAGS, "View Source..."
        ),
        Kr::contextMenuItem(Model::bind(SidePanel::DEVELOPER_TOOLS), Mdi::BUTTON_CURSOR, "Inspect"),
    });
}

Ui::Child inspectorContent(State const &s) {
    if (not s.dom) {
        return Ui::labelMedium(Ui::GRAY500, "No document") |
               Ui::center();
    }

    return Vaev::View::inspect(s.dom.unwrap()) | Ui::vhscroll();
}

Ui::Child sidePanel(State const &s) {
    switch (s.sidePanel) {
    case SidePanel::DEVELOPER_TOOLS:
        return Kr::sidePanelContent({
            Kr::sidePanelTitle(Model::bind(SidePanel::CLOSE), "Inspector"),
            Ui::separator(),
            inspectorContent(s) | Ui::grow(),
        });

    default:
        return Ui::empty();
    }
}

Ui::Child alert(State const &s, String title, String body) {
    return Kr::errorPageContent({
        Kr::errorPageTitle(Mdi::ALERT_DECAGRAM, title),
        Kr::errorPageBody(body),
        Kr::errorPageFooter({
            Ui::button(Model::bindIf<GoBack>(s.canGoBack()), "Go Back"),
            Ui::button(Model::bind<Reload>(), Ui::ButtonStyle::primary(), "Reload"),
        }),
    });
}

Ui::Child webview(State const &s) {
    if (not s.dom)
        return alert(s, "The page could not be loaded"s, Io::toStr(s.dom).unwrap());

    return Vaev::View::view(s.dom.unwrap()) |
           Ui::vscroll() |
           Ui::box({
               .backgroundFill = Gfx::WHITE,
           }) |
           Kr::contextMenu(slot$(contextMenu(s)));
}

Ui::Child appContent(State const &s) {
    if (s.sidePanel == SidePanel::CLOSE)
        return webview(s);
    return Ui::hflow(
        webview(s) | Ui::grow(),
        Ui::separator(),
        sidePanel(s)
    );
}

Ui::Child app(Mime::Url url, Res<Strong<Vaev::Dom::Document>> dom) {
    return Ui::reducer<Model>(
        {
            url,
            dom,
        },
        [](State const &s) {
            return Ui::vflow(
                       Hideo::toolbar(
                           Ui::button(
                               [&](Ui::Node &n) {
                                   Ui::showDialog(n, Kr::alert("Vaev"s, "Copyright © 2024, Odoo S.A."s));
                               },
                               Ui::ButtonStyle::subtle(),
                               Mdi::SURFING
                           ),
                           addressBar(s.url) | Ui::grow(), Ui::button(Model::bind<Reload>(), Ui::ButtonStyle::subtle(), Mdi::REFRESH), Ui::button([&](Ui::Node &n) {
                               Ui::showPopover(n, n.bound().bottomEnd(), mainMenu(s));
                           },
                                                                                                                                                  Ui::ButtonStyle::subtle(), Mdi::DOTS_HORIZONTAL),
                           Hideo::controls()
                       ) | Ui::dragRegion(),
                       appContent(s) | Ui::grow()
                   ) |
                   Ui::pinSize({800, 600}) | Ui::dialogLayer() | Ui::popoverLayer();

            return Hideo::scafold({
                .icon = Mdi::SURFING,
                .title = "Vaev"s,
                .startTools = slots$(
                    Ui::button(Model::bind<Reload>(), Ui::ButtonStyle::subtle(), Mdi::REFRESH)
                ),
                .midleTools = slots$(addressBar(s.url) | Ui::grow()),
                .endTools = slots$(
                    Ui::button(
                        [&](Ui::Node &n) {
                            Ui::showPopover(n, n.bound().bottomEnd(), mainMenu(s));
                        },
                        Ui::ButtonStyle::subtle(),
                        Mdi::DOTS_HORIZONTAL
                    )
                ),
                .body = slot$(appContent(s)),
            });
        }
    );
}

} // namespace Hideo::Browser
