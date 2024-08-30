#include <karm-io/emit.h>
#include <karm-io/funcs.h>
#include <karm-sys/entry.h>
#include <karm-sys/file.h>
#include <vaev-style/styles.h>

Async::Task<> entryPointAsync(Sys::Context &ctx) {
    auto args = Sys::useArgs(ctx);

    if (args.len() != 1) {
        Sys::errln("usage: vaev-style.cli <verb>\n");
        co_return Error::invalidInput();
    }

    auto verb = args[0];

    if (verb == "list-props") {
        Vaev::Style::StyleProp::any([]<typename T>(Meta::Type<T>) {
            Sys::println("{}", T::name());
            return false;
        });
        co_return Ok();
    } else {
        Sys::errln("unknown verb: {} (expected: list-props)\n", verb);
        co_return Error::invalidInput();
    }
}
