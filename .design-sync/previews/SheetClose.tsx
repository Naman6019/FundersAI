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

export function CloseInSheet() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Export data</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Export portfolio overlap</SheetTitle>
          <SheetDescription>
            Choose a format to export the fund comparison results.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Dismiss</Button>} />
          <Button>Export as CSV</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
