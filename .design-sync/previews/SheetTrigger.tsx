import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
  Button,
} from 'marketmind';

export function OpenFromTrigger() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">View holdings</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Fund holdings</SheetTitle>
          <SheetDescription>
            Top 10 equity holdings as of the latest portfolio disclosure.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Close</Button>} />
          <Button>Download PDF</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
